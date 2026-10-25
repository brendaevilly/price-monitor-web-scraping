"""Ciclo completo de monitoramento: coleta -> histórico -> análise -> alerta.

Liga os três serviços para o agendador (RF06, RF12, RF15; issue #66).

Regra central (RN09): só uma coleta VÁLIDA dispara análise e alerta. Coleta
inválida já foi gravada pelo ColetaService (sem apagar o histórico) e o ciclo
termina ali para aquele produto.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alerta import Alerta
from app.models.historico_preco import HistoricoPreco
from app.models.produto import Produto
from app.services.alerta_service import AlertaService, Analise
from app.services.analise_service import AnaliseService, ResultadoAnalise
from app.services.coleta_service import ColetaService, ResultadoColeta

logger = logging.getLogger(__name__)


@dataclass
class ResultadoProduto:
    """O que aconteceu com um produto no ciclo."""

    coleta: ResultadoColeta
    analise: Optional[ResultadoAnalise] = None
    alertas: list[Alerta] = field(default_factory=list)
    alertas_ignorados: int = 0
    erro: Optional[str] = None


@dataclass
class ResultadoCiclo:
    produtos: list[ResultadoProduto] = field(default_factory=list)

    @property
    def coletas(self) -> list[ResultadoColeta]:
        return [item.coleta for item in self.produtos]

    @property
    def validas(self) -> int:
        return sum(1 for item in self.produtos if item.coleta.coleta_valida)

    @property
    def analisados(self) -> int:
        return sum(1 for item in self.produtos if item.analise is not None)

    @property
    def alertas_enviados(self) -> int:
        return sum(len(item.alertas) for item in self.produtos)


def montar_analise_alerta(resultado: ResultadoAnalise, preco_anterior: Optional[Decimal]) -> Analise:
    """Converte o ResultadoAnalise (UC11) no contrato de entrada do AlertaService (UC13).

    `queda_percentual` leva a maior queda positiva entre a comparação com a
    média histórica e com a coleta anterior (RN06 fala em "OU"). Assim a RN07
    (queda >= 5%) também vale enquanto o histórico ainda é curto demais para
    a média (RN10). `houve_queda_relevante` repassa a faixa relevante/grande.
    """
    quedas = [
        v
        for v in (resultado.variacao_percentual_media, resultado.variacao_percentual_anterior)
        if v is not None and v > 0
    ]
    queda = Decimal(str(round(max(quedas), 4))) if quedas else None
    return Analise(
        preco_atual=resultado.preco_atual,
        preco_anterior=preco_anterior,
        media_historica=resultado.media_historica,
        queda_percentual=queda,
        classificacao=resultado.classificacao.value,
        houve_queda_relevante=resultado.queda_relevante,
    )


class CicloMonitoramentoService:
    def __init__(
        self,
        coleta: Optional[ColetaService] = None,
        analise: Optional[AnaliseService] = None,
        alerta: Optional[AlertaService] = None,
    ):
        self.coleta = coleta or ColetaService()
        self.analise = analise or AnaliseService()
        self.alerta = alerta or AlertaService()

    def executar_ciclo(self, db: Session) -> ResultadoCiclo:
        """Coleta todos os produtos ativos e, após cada coleta válida, analisa e alerta."""
        ciclo = ResultadoCiclo()

        def depois_da_coleta(produto: Produto, coleta: ResultadoColeta) -> None:
            ciclo.produtos.append(self.processar_coleta(db, produto, coleta))

        self.coleta.executar_coleta_ativos(db, ao_coletar=depois_da_coleta)
        return ciclo

    def processar_coleta(
        self, db: Session, produto: Produto, coleta: ResultadoColeta
    ) -> ResultadoProduto:
        """Pós-coleta de um produto. Nunca propaga exceção (um produto não derruba os outros)."""
        item = ResultadoProduto(coleta=coleta)

        # RN09: coleta inválida não gera análise nem alerta.
        if not coleta.coleta_valida:
            logger.info(
                "Produto %s: coleta inválida, análise e alerta não executados (RN09).",
                produto.id,
            )
            return item

        try:
            historico = (
                db.query(HistoricoPreco)
                .filter(HistoricoPreco.produto_id == produto.id)
                .order_by(HistoricoPreco.data_hora_coleta)
                .all()
            )
            item.analise = self.analise.classificar(historico)

            validos = [h for h in historico if h.coleta_valida and h.preco is not None and h.preco > 0]
            preco_anterior = validos[-2].preco if len(validos) >= 2 else None

            avaliacao = self.alerta.avaliar_condicoes(
                produto, montar_analise_alerta(item.analise, preco_anterior), db
            )
            item.alertas = avaliacao.alertas
            item.alertas_ignorados = avaliacao.ignorados
            logger.info(
                "Produto %s: %s, %s alerta(s) enviado(s), %s ignorado(s).",
                produto.id,
                item.analise.classificacao.value,
                len(item.alertas),
                item.alertas_ignorados,
            )
        except Exception as exc:
            db.rollback()
            item.erro = str(exc)
            logger.exception("Falha na análise/alerta do produto %s.", produto.id)
        return item
