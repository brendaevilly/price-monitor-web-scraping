"""Robô de scraping de preços (RF06, RF07, RF08).

Sites do MVP: Mercado Livre e Magazine Luiza. Também há extratores para
Amazon BR e Kabum, para books.toscrape.com (demonstração) e um fallback
genérico (JSON-LD / meta tags). Os extratores ficam num registro
(`EXTRATORES`), escolhido pelo domínio da loja.

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
from typing import Callable, Optional
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


def _normalizar_dominio_bruto(dominio: str) -> str:
    dominio = (dominio or "").strip().lower()
    return dominio[4:] if dominio.startswith("www.") else dominio


def identificar_dominio(produto: Produto, loja: Optional[Loja]) -> str:
    """Domínio (minúsculo, sem 'www.') usado para escolher o extrator.

    Prioriza o domínio da Loja cadastrada; sem loja, cai para o hostname da
    URL do produto.
    """
    if loja and loja.dominio:
        return _normalizar_dominio_bruto(loja.dominio)
    hostname = urlparse(produto.url_produto or "").hostname or ""
    return _normalizar_dominio_bruto(hostname)


def _extrair_por_seletores(soup: BeautifulSoup, seletores: tuple[str, ...]) -> Optional[Decimal]:
    """Tenta cada seletor CSS e devolve o primeiro preço válido."""
    for seletor in seletores:
        elemento = soup.select_one(seletor)
        if elemento is None:
            continue
        preco = normalizar_preco(elemento.get("content") or elemento.get_text(" ", strip=True))
        if preco is not None:
            return preco
    return None


def extrair_preco_books_toscrape(soup: BeautifulSoup, html: str = "") -> Optional[Decimal]:
    elemento = soup.select_one(".price_color")
    if elemento is None:
        return None
    return normalizar_preco(elemento.get_text())


def extrair_preco_magazineluiza(soup: BeautifulSoup, html: str) -> Optional[Decimal]:
    """Magazine Luiza: JSON-LD, meta tags e, por último, o bloco de preço da página."""
    preco = extrair_preco_json_ld(html)
    if preco is not None:
        return preco
    preco = extrair_preco_meta(soup)
    if preco is not None:
        return preco
    return _extrair_por_seletores(
        soup,
        (
            '[data-testid="price-value"]',
            '[data-testid="price-default"]',
            '[data-testid="product-price"]',
        ),
    )


def extrair_preco_amazon(soup: BeautifulSoup, html: str) -> Optional[Decimal]:
    """Amazon BR: JSON-LD/meta (raros) e o bloco `a-price` da página."""
    preco = extrair_preco_json_ld(html)
    if preco is not None:
        return preco
    preco = extrair_preco_meta(soup)
    if preco is not None:
        return preco
    return _extrair_por_seletores(
        soup,
        (
            "#corePrice_feature_div .a-price .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "span.a-price span.a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
        ),
    )


def extrair_preco_kabum(soup: BeautifulSoup, html: str) -> Optional[Decimal]:
    """Kabum: JSON-LD, meta tags e a classe de preço final da página."""
    preco = extrair_preco_json_ld(html)
    if preco is not None:
        return preco
    preco = extrair_preco_meta(soup)
    if preco is not None:
        return preco
    return _extrair_por_seletores(soup, ("h4.finalPrice", ".finalPrice", "#blocoValores .finalPrice"))


@dataclass(frozen=True)
class Extrator:
    """Associa trechos de domínio a uma função de extração (RF07)."""

    nome: str
    dominios: tuple[str, ...]
    funcao: Callable[[BeautifulSoup, str], Optional[Decimal]]

    def atende(self, dominio: str) -> bool:
        return any(trecho in dominio for trecho in self.dominios)


# Para incluir outra loja: escreva `extrair_preco_<loja>(soup, html)`,
# registre aqui e cadastre a Loja (ver app/seed_lojas.py).
EXTRATORES: tuple[Extrator, ...] = (
    Extrator("Mercado Livre", ("mercadolivre", "mercadolibre"), extrair_preco_mercadolivre),
    Extrator("Magazine Luiza", ("magazineluiza", "magalu.com"), extrair_preco_magazineluiza),
    Extrator("Amazon BR", ("amazon.com.br",), extrair_preco_amazon),
    Extrator("Kabum", ("kabum.com.br",), extrair_preco_kabum),
    Extrator("Books to Scrape (demo)", ("books.toscrape.com",), extrair_preco_books_toscrape),
)


def selecionar_extrator(dominio: str) -> Optional[Extrator]:
    """Extrator específico do domínio, ou None (usa o fallback genérico)."""
    dominio = _normalizar_dominio_bruto(dominio)
    for extrator in EXTRATORES:
        if extrator.atende(dominio):
            return extrator
    return None


_MARCADORES_BLOQUEIO = (
    "suspicious-traffic",
    "gz-account-verification",
    "/errors/validatecaptcha",  # Amazon: página de captcha
    "digite os caracteres que você vê abaixo",
)


def _pagina_bloqueada(html: str) -> bool:
    html_lower = html.lower()
    return any(marcador in html_lower for marcador in _MARCADORES_BLOQUEIO)


def _erro_nao_retriavel(exc: Exception) -> bool:
    """4xx permanentes (ex.: 404) não melhoram na próxima tentativa."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        codigo = exc.response.status_code
        return 400 <= codigo < 500 and codigo not in {408, 429}
    return False


def extrair_preco(html: str, dominio: str) -> Optional[Decimal]:
    """Escolhe o extrator pelo domínio da loja; sem extrator, usa o genérico."""
    soup = BeautifulSoup(html, "html.parser")
    extrator = selecionar_extrator(dominio)
    if extrator is not None:
        return extrator.funcao(soup, html)
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
                if _erro_nao_retriavel(exc):
                    return self._registrar_falha(
                        db, produto, tentativas=tentativa, erro=ultimo_erro
                    )
                if tentativa < max_tentativas:
                    self._aguardar_intervalo()

        return self._registrar_falha(db, produto, tentativas=max_tentativas, erro=ultimo_erro)

    def executar_coleta_ativos(
        self,
        db: Session,
        ao_coletar: Optional[Callable[[Produto, ResultadoColeta], None]] = None,
    ) -> list[ResultadoColeta]:
        """Coleta todos os produtos ativos — ponto de entrada para o agendador (RF06).

        `ao_coletar(produto, resultado)`, se informado, roda logo depois de cada
        coleta (válida ou não). É por ele que o agendador encadeia análise e
        alerta (issue #66). Erro no callback é registrado e não interrompe a
        coleta dos demais produtos.
        """
        produtos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
        resultados: list[ResultadoColeta] = []
        for produto in produtos:
            resultado = self.executar_coleta(produto, db)
            resultados.append(resultado)
            if ao_coletar is not None:
                try:
                    ao_coletar(produto, resultado)
                except Exception:
                    logger.exception(
                        "Falha no pós-processamento do produto %s.", produto.id
                    )
        return resultados

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
