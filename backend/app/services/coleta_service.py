"""Robô de scraping de preços (RF06, RF07, RF08).

Site do MVP: Mercado Livre. Também há extrator para books.toscrape.com
(demonstração) e fallback genérico (JSON-LD / meta tags).

A extração usa BeautifulSoup + Requests, respeita intervalo mínimo e
limite de tentativas (RNF08) e persiste HistoricoPreco sem apagar
coletas anteriores em caso de falha (UC12, RN09, RN14).
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.produto import Produto

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

_RE_DIGITO_PRECO = re.compile(r"[^\d,.]")


@dataclass
class ResultadoColeta:
    sucesso: bool
    produto_id: UUID
    preco: Optional[Decimal]
    coleta_valida: bool
    tentativas: int
    historico_id: Optional[UUID] = None
    erro: Optional[str] = None


def normalizar_preco(valor: str | int | float | Decimal | None) -> Optional[Decimal]:
    """Converte textos como 'R$ 1.299,90' ou '1299.90' em Decimal positivo."""
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        texto = format(valor, "f")
    else:
        texto = str(valor).strip()
    if not texto:
        return None

    texto = _RE_DIGITO_PRECO.sub("", texto)
    if not texto or texto in {".", ","}:
        return None

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        preco = Decimal(texto)
    except InvalidOperation:
        return None

    if preco <= 0:
        return None
    return preco.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _buscar_preco_em_json(dados) -> Optional[Decimal]:
    if isinstance(dados, list):
        for item in dados:
            encontrado = _buscar_preco_em_json(item)
            if encontrado is not None:
                return encontrado
        return None

    if not isinstance(dados, dict):
        return None

    if "@graph" in dados:
        encontrado = _buscar_preco_em_json(dados["@graph"])
        if encontrado is not None:
            return encontrado

    ofertas = dados.get("offers")
    if isinstance(ofertas, list) and ofertas:
        ofertas = ofertas[0]
    if isinstance(ofertas, dict):
        for chave in ("price", "lowPrice"):
            preco = normalizar_preco(ofertas.get(chave))
            if preco is not None:
                return preco

    return normalizar_preco(dados.get("price"))


def extrair_preco_json_ld(html: str) -> Optional[Decimal]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        conteudo = script.string or script.get_text() or ""
        if not conteudo.strip():
            continue
        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError:
            continue
        preco = _buscar_preco_em_json(dados)
        if preco is not None:
            return preco
    return None


def extrair_preco_meta(soup: BeautifulSoup) -> Optional[Decimal]:
    seletores = [
        ("meta", {"itemprop": "price"}),
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "og:price:amount"}),
        ("span", {"itemprop": "price"}),
        ("div", {"itemprop": "price"}),
    ]
    for tag, attrs in seletores:
        elemento = soup.find(tag, attrs=attrs)
        if elemento is None:
            continue
        bruto = elemento.get("content") or elemento.get_text()
        preco = normalizar_preco(bruto)
        if preco is not None:
            return preco
    return None


def extrair_preco_mercadolivre(soup: BeautifulSoup, html: str) -> Optional[Decimal]:
    """Extrai o preço de uma página de produto do Mercado Livre (site do MVP)."""
    preco = extrair_preco_json_ld(html)
    if preco is not None:
        return preco

    preco = extrair_preco_meta(soup)
    if preco is not None:
        return preco

    fracao = soup.select_one(".andes-money-amount__fraction")
    if fracao is not None:
        texto = fracao.get_text(strip=True)
        centavos = soup.select_one(".andes-money-amount__cents")
        if centavos is not None:
            texto = f"{texto},{centavos.get_text(strip=True)}"
        preco = normalizar_preco(texto)
        if preco is not None:
            return preco

    return None


def extrair_preco_generico(soup: BeautifulSoup, html: str) -> Optional[Decimal]:
    preco = extrair_preco_json_ld(html)
    if preco is not None:
        return preco
    return extrair_preco_meta(soup)


def identificar_dominio(produto: Produto, loja: Optional[Loja]) -> str:
    if loja and loja.dominio:
        return loja.dominio.lower()
    hostname = urlparse(produto.url_produto).hostname or ""
    return hostname.lower()


def extrair_preco_books_toscrape(soup: BeautifulSoup) -> Optional[Decimal]:
    elemento = soup.select_one(".price_color")
    if elemento is None:
        return None
    return normalizar_preco(elemento.get_text())


def _pagina_bloqueada(html: str) -> bool:
    html_lower = html.lower()
    return "suspicious-traffic" in html_lower or "gz-account-verification" in html_lower


def extrair_preco(html: str, dominio: str) -> Optional[Decimal]:
    soup = BeautifulSoup(html, "html.parser")
    if "mercadolivre" in dominio or "mercadolibre" in dominio:
        return extrair_preco_mercadolivre(soup, html)
    if "books.toscrape.com" in dominio:
        return extrair_preco_books_toscrape(soup)
    return extrair_preco_generico(soup, html)


class ColetaService:
    """Orquestra a coleta de um produto e a persistência do histórico."""

    _lock = threading.Lock()
    _ultima_requisicao_em: float = 0.0

    def executarColeta(self, produto: Produto, db: Optional[Session] = None) -> ResultadoColeta:
        """Nome do caso de uso (UC12). Encaminha para executar_coleta."""
        return self.executar_coleta(produto, db)

    def executar_coleta(self, produto: Produto, db: Optional[Session] = None) -> ResultadoColeta:
        fechar_sessao = False
        if db is None:
            from app.database import SessionLocal

            db = SessionLocal()
            fechar_sessao = True

        try:
            return self._executar_coleta(produto, db)
        finally:
            if fechar_sessao:
                db.close()

    def _executar_coleta(self, produto: Produto, db: Session) -> ResultadoColeta:
        if not produto.url_produto:
            return self._registrar_falha(
                db, produto, tentativas=0, erro="Produto sem URL para coleta."
            )

        loja = db.get(Loja, produto.loja_id)
        dominio = identificar_dominio(produto, loja)
        max_tentativas = max(1, settings.COLETA_MAX_TENTATIVAS)
        ultimo_erro = "Falha desconhecida na extração."

        for tentativa in range(1, max_tentativas + 1):
            try:
                resposta = self._requisitar(produto.url_produto)
                resposta.raise_for_status()
                if _pagina_bloqueada(resposta.text):
                    raise ValueError(
                        "A loja bloqueou a requisição automática "
                        "(página de verificação de tráfego)."
                    )
                preco = extrair_preco(resposta.text, dominio)
                if preco is None:
                    raise ValueError("Preço não encontrado na página do produto.")

                historico = HistoricoPreco(
                    produto_id=produto.id,
                    preco=preco,
                    coleta_valida=True,
                )
                db.add(historico)
                db.commit()
                db.refresh(historico)
                logger.info(
                    "Coleta válida do produto %s: R$ %s (tentativa %s)",
                    produto.id,
                    preco,
                    tentativa,
                )
                return ResultadoColeta(
                    sucesso=True,
                    produto_id=produto.id,
                    preco=preco,
                    coleta_valida=True,
                    tentativas=tentativa,
                    historico_id=historico.id,
                )
            except Exception as exc:
                ultimo_erro = str(exc)
                logger.warning(
                    "Tentativa %s/%s falhou para o produto %s: %s",
                    tentativa,
                    max_tentativas,
                    produto.id,
                    ultimo_erro,
                )
                if tentativa < max_tentativas:
                    self._aguardar_intervalo()

        return self._registrar_falha(db, produto, tentativas=max_tentativas, erro=ultimo_erro)

    def executar_coleta_ativos(self, db: Session) -> list[ResultadoColeta]:
        """Coleta todos os produtos ativos — ponto de entrada para o agendador (RF06)."""
        produtos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
        return [self.executar_coleta(produto, db) for produto in produtos]

    def _requisitar(self, url: str) -> requests.Response:
        self._aguardar_intervalo()
        return requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
            timeout=settings.COLETA_TIMEOUT_SEGUNDOS,
            allow_redirects=True,
        )

    def _aguardar_intervalo(self) -> None:
        intervalo = max(0.0, settings.COLETA_INTERVALO_MINIMO_SEGUNDOS)
        with self._lock:
            agora = time.monotonic()
            decorrido = agora - ColetaService._ultima_requisicao_em
            if ColetaService._ultima_requisicao_em > 0 and decorrido < intervalo:
                time.sleep(intervalo - decorrido)
            ColetaService._ultima_requisicao_em = time.monotonic()

    def _registrar_falha(
        self,
        db: Session,
        produto: Produto,
        tentativas: int,
        erro: str,
    ) -> ResultadoColeta:
        """Registra a falha sem apagar o histórico anterior (RN09, RN14)."""
        ultimo = (
            db.query(HistoricoPreco)
            .filter(HistoricoPreco.produto_id == produto.id)
            .order_by(HistoricoPreco.data_hora_coleta.desc())
            .first()
        )
        preco_referencia = ultimo.preco if ultimo is not None else Decimal("0.00")

        historico = HistoricoPreco(
            produto_id=produto.id,
            preco=preco_referencia,
            coleta_valida=False,
        )
        db.add(historico)
        db.commit()
        db.refresh(historico)
        logger.error(
            "Coleta inválida do produto %s após %s tentativa(s): %s. "
            "Histórico anterior preservado.",
            produto.id,
            tentativas,
            erro,
        )
        return ResultadoColeta(
            sucesso=False,
            produto_id=produto.id,
            preco=None,
            coleta_valida=False,
            tentativas=tentativas,
            historico_id=historico.id,
            erro=erro,
        )
