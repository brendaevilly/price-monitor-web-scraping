"""AlertaService — disparo de alerta por e-mail (RF15, RF16, UC13).

Dispara quando há queda de 5%+ ou preço-alvo atingido (RN07).
Não reenvia a mesma ocorrência dentro do intervalo configurado (RN08, RN11).
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.alerta import Alerta
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.models.usuario import Usuario

logger = logging.getLogger(__name__)

TIPO_QUEDA = "queda_preco"
TIPO_PRECO_ALVO = "preco_alvo"


@dataclass
class Analise:
    """Contrato de entrada do AlertaService (preenchido pelo AnaliseService)."""

    preco_atual: Decimal
    preco_anterior: Optional[Decimal] = None
    media_historica: Optional[Decimal] = None
    queda_percentual: Optional[Decimal] = None
    classificacao: Optional[str] = None
    houve_queda_relevante: bool = False


@dataclass
class ResultadoAvaliacao:
    alertas: list[Alerta]
    ignorados: int


class AlertaService:
    def avaliarCondicoes(
        self,
        produto: Produto,
        analise: Analise,
        db: Optional[Session] = None,
    ) -> ResultadoAvaliacao:
        """Nome do caso de uso (UC13). Encaminha para avaliar_condicoes."""
        return self.avaliar_condicoes(produto, analise, db)

    def enviarEmail(
        self,
        alerta: Alerta,
        destinatario: str,
        produto: Produto,
        nome_usuario: Optional[str] = None,
    ) -> None:
        """Nome do caso de uso (UC13). Encaminha para enviar_email."""
        return self.enviar_email(alerta, destinatario, produto, nome_usuario)

    def avaliar_condicoes(
        self,
        produto: Produto,
        analise: Analise,
        db: Optional[Session] = None,
    ) -> ResultadoAvaliacao:
        fechar_sessao = False
        if db is None:
            from app.database import SessionLocal

            db = SessionLocal()
            fechar_sessao = True

        try:
            return self._avaliar_condicoes(produto, analise, db)
        finally:
            if fechar_sessao:
                db.close()

    def _avaliar_condicoes(
        self,
        produto: Produto,
        analise: Analise,
        db: Session,
    ) -> ResultadoAvaliacao:
        preco_atual = _decimal(analise.preco_atual)
        disparar_queda = self._queda_dispara_alerta(analise)
        queda = self._percentual_queda(analise)

        monitoramentos = (
            db.query(Monitoramento)
            .filter(
                Monitoramento.produto_id == produto.id,
                Monitoramento.alerta_ativo.is_(True),
            )
            .all()
        )

        criados: list[Alerta] = []
        ignorados = 0

        for monitoramento in monitoramentos:
            disparos: list[tuple[str, str]] = []
            if disparar_queda:
                texto_queda = (
                    f"{queda:.2f}%" if queda is not None else "relevante"
                )
                disparos.append(
                    (
                        TIPO_QUEDA,
                        (
                            f"Queda de {texto_queda} no produto '{produto.nome}'. "
                            f"Preço atual: R$ {preco_atual:.2f}."
                        ),
                    )
                )
            if self._preco_alvo_atingido(monitoramento, preco_atual):
                disparos.append(
                    (
                        TIPO_PRECO_ALVO,
                        (
                            f"Preço-alvo de R$ {_decimal(monitoramento.preco_alvo):.2f} "
                            f"atingido em '{produto.nome}'. "
                            f"Preço atual: R$ {preco_atual:.2f}."
                        ),
                    )
                )

            for tipo, mensagem in disparos:
                if self._ja_enviado_recentemente(db, produto.id, monitoramento.usuario_id, tipo):
                    ignorados += 1
                    logger.info(
                        "Alerta %s do produto %s para o usuário %s ignorado (RN08/RN11).",
                        tipo,
                        produto.id,
                        monitoramento.usuario_id,
                    )
                    continue

                destinatario = self._obter_email(monitoramento.usuario_id)
                if not destinatario:
                    logger.error(
                        "Usuário %s sem e-mail no Supabase Auth; alerta %s não enviado.",
                        monitoramento.usuario_id,
                        tipo,
                    )
                    continue

                usuario = db.get(Usuario, monitoramento.usuario_id)
                nome_usuario = usuario.nome if usuario is not None else None
                alerta = Alerta(
                    produto_id=produto.id,
                    usuario_id=monitoramento.usuario_id,
                    tipo=tipo,
                    mensagem=mensagem,
                )
                try:
                    self.enviar_email(alerta, destinatario, produto, nome_usuario)
                except Exception:
                    logger.exception(
                        "Falha ao enviar e-mail de alerta %s do produto %s.",
                        tipo,
                        produto.id,
                    )
                    continue

                db.add(alerta)
                db.commit()
                db.refresh(alerta)
                criados.append(alerta)

        return ResultadoAvaliacao(alertas=criados, ignorados=ignorados)

    def enviar_email(
        self,
        alerta: Alerta,
        destinatario: str,
        produto: Produto,
        nome_usuario: Optional[str] = None,
    ) -> None:
        assunto, corpo = self._montar_mensagem(alerta, produto, nome_usuario)
        remetente = settings.SMTP_FROM or settings.SMTP_USER

        if settings.ALERTA_SMTP_DRY_RUN:
            logger.info(
                "[dry-run] Alerta %s para %s | %s | %s",
                alerta.tipo,
                destinatario,
                assunto,
                corpo,
            )
            return

        if not settings.SMTP_HOST or not remetente:
            raise RuntimeError(
                "SMTP não configurado. Defina SMTP_HOST e SMTP_FROM (ou SMTP_USER) no .env."
            )

        mensagem = EmailMessage()
        mensagem["Subject"] = assunto
        mensagem["From"] = remetente
        mensagem["To"] = destinatario
        mensagem.set_content(corpo)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as servidor:
            if settings.SMTP_USAR_TLS:
                servidor.starttls()
            if settings.SMTP_USER:
                servidor.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            servidor.send_message(mensagem)

        logger.info("E-mail de alerta %s enviado para %s.", alerta.tipo, destinatario)

    def _queda_dispara_alerta(self, analise: Analise) -> bool:
        if getattr(analise, "houve_queda_relevante", False):
            return True
        queda = self._percentual_queda(analise)
        minimo = Decimal(str(settings.ALERTA_QUEDA_MINIMA_PERCENTUAL))
        return queda is not None and queda >= minimo

    def _percentual_queda(self, analise: Analise) -> Optional[Decimal]:
        queda = getattr(analise, "queda_percentual", None)
        if queda is not None:
            return _decimal(queda)

        anterior = getattr(analise, "preco_anterior", None)
        atual = getattr(analise, "preco_atual", None)
        if anterior is None or atual is None:
            return None
        anterior_d = _decimal(anterior)
        atual_d = _decimal(atual)
        if anterior_d <= 0 or atual_d >= anterior_d:
            return None
        return ((anterior_d - atual_d) / anterior_d) * Decimal("100")

    def _preco_alvo_atingido(self, monitoramento: Monitoramento, preco_atual: Decimal) -> bool:
        if monitoramento.preco_alvo is None:
            return False
        return preco_atual <= _decimal(monitoramento.preco_alvo)

    def _ja_enviado_recentemente(
        self,
        db: Session,
        produto_id: UUID,
        usuario_id: UUID,
        tipo: str,
    ) -> bool:
        horas = max(1, settings.ALERTA_INTERVALO_REENVIOS_HORAS)
        limite = datetime.now(timezone.utc) - timedelta(hours=horas)
        ultimo = (
            db.query(Alerta)
            .filter(
                Alerta.produto_id == produto_id,
                Alerta.usuario_id == usuario_id,
                Alerta.tipo == tipo,
                Alerta.data_envio >= limite,
            )
            .first()
        )
        return ultimo is not None

    def _obter_email(self, usuario_id: UUID) -> Optional[str]:
        from app.database import supabase

        try:
            resposta = supabase.auth.admin.get_user_by_id(str(usuario_id))
        except Exception:
            logger.exception("Não foi possível buscar o e-mail do usuário %s.", usuario_id)
            return None

        user = getattr(resposta, "user", None)
        email = getattr(user, "email", None) if user is not None else None
        return email or None

    def _montar_mensagem(
        self,
        alerta: Alerta,
        produto: Produto,
        nome_usuario: Optional[str] = None,
    ) -> tuple[str, str]:
        if alerta.tipo == TIPO_PRECO_ALVO:
            assunto = f"PriceBrother: preço-alvo atingido em {produto.nome}"
        else:
            assunto = f"PriceBrother: queda de preço em {produto.nome}"

        saudacao = f"Olá, {nome_usuario}!\n\n" if nome_usuario else ""
        corpo = (
            f"{saudacao}{alerta.mensagem}\n\n"
            f"Produto: {produto.nome}\n"
            f"Link: {produto.url_produto}\n\n"
            "Você recebeu este e-mail porque monitora este produto no PriceBrother.\n"
        )
        return assunto, corpo


def _decimal(valor) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))
