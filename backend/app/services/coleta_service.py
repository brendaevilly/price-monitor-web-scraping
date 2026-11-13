"""Robô de scraping de preços (RF06, RF07, RF08).

Frete (issue #105): quando a página mostra o frete, ele entra na medição:
`HistoricoPreco.preco` guarda produto + frete e `HistoricoPreco.frete` guarda
só o frete (0 = grátis, NULL = não informado na página).

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
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.config import settings
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.produto import Produto
from app.services import navegador

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

_RE_DIGITO_PRECO = re.compile(r"[^\d,.]")


# Motivos de falha de coleta (ResultadoColeta.motivo_falha e logs).
MOTIVO_LAYOUT = "layout_alterado"   # a página veio, mas o extrator não achou o preço
MOTIVO_BLOQUEIO = "bloqueio"        # captcha / verificação de tráfego
MOTIVO_HTTP = "http"                # resposta 4xx/5xx
MOTIVO_REDE = "rede"                # timeout, DNS, conexão recusada
MOTIVO_SEM_URL = "sem_url"
MOTIVO_BANCO = "banco"              # preço extraído, mas não foi possível gravar
MOTIVO_INESPERADO = "inesperado"


class FalhaColeta(Exception):
    """Falha de coleta com motivo classificado (para log e ResultadoColeta)."""

    def __init__(self, motivo: str, mensagem: str):
        super().__init__(mensagem)
        self.motivo = motivo


def _classificar_falha(exc: Exception) -> str:
    if isinstance(exc, FalhaColeta):
        return exc.motivo
    if isinstance(exc, requests.HTTPError):
        return MOTIVO_HTTP
    if isinstance(exc, requests.RequestException):
        return MOTIVO_REDE
    return MOTIVO_INESPERADO


@dataclass
class ResultadoColeta:
    sucesso: bool
    produto_id: UUID
    preco: Optional[Decimal]
    coleta_valida: bool
    tentativas: int
    historico_id: Optional[UUID] = None
    erro: Optional[str] = None
<<<<<<< HEAD
    # Issue #105: `preco` é o valor medido (produto + frete). 0 = frete grátis;
    # None = a página não informou o frete (então `preco` é só o produto).
    frete: Optional[Decimal] = None
    preco_produto: Optional[Decimal] = None
=======
    motivo_falha: Optional[str] = None
>>>>>>> fc95810ab81209f9418926a060684f6f9af4bddb


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


# ---------- frete (issue #105) ----------

_RE_ATRIBUTO_FRETE = re.compile(r"frete|shipping|delivery|entrega|envio", re.IGNORECASE)
_RE_FRETE_CONDICIONAL = re.compile(
    r"gr[áa]tis\s+(?:\w+\s+){0,3}?(?:acima|a partir|para compras|em compras|nas compras|"
    r"na compra|nos pedidos|em pedidos)"
)
_RE_FRETE_GRATIS = re.compile(
    r"(?:frete|entrega|envio)\s+(?:\w+\s+){0,2}?gr[áa]tis|chega(?:r[áa])?\s+gr[áa]tis|"
    r"gr[áa]tis\s+(?:de\s+)?(?:frete|entrega|envio)"
)
_VALOR_BR = r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)"
_RE_FRETE_VALOR = re.compile(
    rf"(?:frete|entrega|envio)[^\d$]{{0,20}}{_VALOR_BR}|{_VALOR_BR}\s+(?:de\s+)?(?:frete|entrega|envio)",
    re.IGNORECASE,
)
_TAGS_IGNORADAS_FRETE = {"script", "style", "noscript", "header", "footer", "nav", "head"}
_MAX_TEXTO_FRETE = 400


def _valor_frete(valor) -> Optional[Decimal]:
    """Converte um valor de frete (aceita 0, ao contrário de `normalizar_preco`)."""
    if valor is None or isinstance(valor, bool):
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return normalizar_preco(texto)
    if not numero.is_finite() or numero < 0:
        return None
    return numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def interpretar_texto_frete(texto: str) -> Optional[Decimal]:
    """Lê o frete de um trecho de texto: 0 (grátis), valor em reais ou None.

    "Frete grátis acima de R$ 99" é condicional (depende do carrinho/CEP), então
    não conta como frete grátis: devolve None.
    """
    texto = " ".join((texto or "").lower().split())
    if not texto:
        return None
    if _RE_FRETE_CONDICIONAL.search(texto):
        return None
    if _RE_FRETE_GRATIS.search(texto):
        return Decimal("0.00")
    achado = _RE_FRETE_VALOR.search(texto)
    if achado:
        bruto = achado.group(1) or achado.group(2)
        return normalizar_preco(bruto)
    return None


def _frete_em_dict_json(dados) -> Optional[Decimal]:
    """schema.org: offers.shippingDetails.shippingRate.value (value pode ser 0)."""
    if isinstance(dados, list):
        for item in dados:
            encontrado = _frete_em_dict_json(item)
            if encontrado is not None:
                return encontrado
        return None
    if not isinstance(dados, dict):
        return None
    if "@graph" in dados:
        encontrado = _frete_em_dict_json(dados["@graph"])
        if encontrado is not None:
            return encontrado

    ofertas = dados.get("offers")
    if isinstance(ofertas, list) and ofertas:
        ofertas = ofertas[0]
    origem = ofertas if isinstance(ofertas, dict) else dados

    detalhes = origem.get("shippingDetails")
    if isinstance(detalhes, list) and detalhes:
        detalhes = detalhes[0]
    if isinstance(detalhes, dict):
        taxa = detalhes.get("shippingRate")
        if isinstance(taxa, list) and taxa:
            taxa = taxa[0]
        if isinstance(taxa, dict):
            return _valor_frete(taxa.get("value", taxa.get("price")))
        return _valor_frete(taxa)
    return None


def extrair_frete_json_ld(html: str) -> Optional[Decimal]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        conteudo = script.string or script.get_text() or ""
        if not conteudo.strip():
            continue
        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError:
            continue
        frete = _frete_em_dict_json(dados)
        if frete is not None:
            return frete
    return None


def _em_regiao_ignorada(tag) -> bool:
    return any(pai.name in _TAGS_IGNORADAS_FRETE for pai in [tag, *tag.parents])


def extrair_frete_texto(soup: BeautifulSoup) -> Optional[Decimal]:
    """Procura o frete em blocos cujo id/classe/data-testid falam de frete/entrega.

    Só olha blocos curtos e fora de cabeçalho/rodapé/menu, para não confundir com
    banners promocionais da loja ("Frete grátis em todo o site").
    """
    for tag in soup.find_all(True):
        if _em_regiao_ignorada(tag):
            continue
        marcas = " ".join(
            [
                tag.get("id") or "",
                " ".join(tag.get("class") or []),
                tag.get("data-testid") or "",
                tag.get("itemprop") or "",
            ]
        )
        if not _RE_ATRIBUTO_FRETE.search(marcas):
            continue
        texto = tag.get_text(" ", strip=True)
        if not texto or len(texto) > _MAX_TEXTO_FRETE:
            continue
        frete = interpretar_texto_frete(texto)
        if frete is not None:
            return frete
    return None


def extrair_frete(html: str) -> Optional[Decimal]:
    """Frete mostrado na página: 0 (grátis), valor em reais ou None (não informado).

    O frete real depende do CEP do comprador; aqui vale o que a página mostra
    sem CEP (dados estruturados primeiro, depois os blocos de entrega).
    """
    frete = extrair_frete_json_ld(html)
    if frete is not None:
        return frete
    return extrair_frete_texto(BeautifulSoup(html, "html.parser"))


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
    "just a moment...",  # Cloudflare
    "cf-challenge",
    "verifying you are human",
    "are you a robot",
    "você é um robô",
    "access denied",
)


def _pagina_bloqueada(html: str) -> bool:
    html_lower = html.lower()
    return any(marcador in html_lower for marcador in _MARCADORES_BLOQUEIO)


_STATUS_BLOQUEIO = {403, 429, 503}


def _precisa_navegador(resposta) -> bool:
    """True se a loja barrou o `requests` (status de bloqueio ou tela de robô)."""
    if getattr(resposta, "status_code", 200) in _STATUS_BLOQUEIO:
        return True
    return _pagina_bloqueada(getattr(resposta, "text", "") or "")


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


def _mensagem_layout_alterado(produto: Produto, loja: Optional[Loja], dominio: str) -> str:
    """Mensagem para quando a página veio mas o extrator não achou o preço.

    Tipicamente a loja mudou o HTML. Diz qual loja, qual extrator e onde olhar,
    para quem lê o log saber que o problema é o seletor, não a rede.
    """
    extrator = selecionar_extrator(dominio)
    nome_extrator = extrator.nome if extrator else "genérico (JSON-LD/meta tags)"
    nome_loja = loja.nome if loja else dominio
    return (
        f"Layout alterado? O extrator '{nome_extrator}' não encontrou o preço na página "
        f"do produto ({produto.url_produto}, loja '{nome_loja}'). O HTML da loja "
        "provavelmente mudou: revise os seletores em coleta_service.EXTRATORES."
    )


def _id_sem_consulta(produto: Produto) -> UUID:
    """Chave primária sem ir ao banco (o objeto pode estar expirado após rollback)."""
    identidade = sa_inspect(produto).identity
    return identidade[0] if identidade else produto.id


def _url_sem_consulta(produto: Produto) -> str:
    """URL só se já estiver carregada; nunca dispara consulta durante o tratamento de falha."""
    return produto.__dict__.get("url_produto") or "(URL indisponível)"


def _rollback_seguro(db: Session) -> None:
    """Desfaz a transação sem deixar o próprio rollback propagar erro."""
    try:
        db.rollback()
    except Exception:
        logger.exception("Falha ao fazer rollback da sessão.")


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
                db,
                produto,
                tentativas=0,
                erro="Produto sem URL para coleta.",
                motivo=MOTIVO_SEM_URL,
            )

        loja = db.get(Loja, produto.loja_id)
        dominio = identificar_dominio(produto, loja)
        max_tentativas = max(1, settings.COLETA_MAX_TENTATIVAS)
        ultimo_erro = "Falha desconhecida na extração."
        ultimo_motivo = MOTIVO_INESPERADO

        for tentativa in range(1, max_tentativas + 1):
            try:
                resposta = self._obter_pagina(produto.url_produto)
                resposta.raise_for_status()
                if _pagina_bloqueada(resposta.text):
                    raise FalhaColeta(
                        MOTIVO_BLOQUEIO,
                        "A loja bloqueou a requisição automática "
                        "(página de verificação de tráfego).",
                    )
<<<<<<< HEAD
                preco_produto = extrair_preco(resposta.text, dominio)
                if preco_produto is None:
                    raise ValueError("Preço não encontrado na página do produto.")

                # Issue #105: o frete entra na medição (produto + frete). Falha
                # ao ler o frete nunca invalida a coleta do preço.
                frete = self._extrair_frete_seguro(resposta.text)
                preco = preco_produto + (frete or Decimal("0.00"))

                historico = HistoricoPreco(
                    produto_id=produto.id,
                    preco=preco,
                    frete=frete,
                    coleta_valida=True,
                )
                db.add(historico)
                db.commit()
                db.refresh(historico)
                logger.info(
                    "Coleta válida do produto %s: R$ %s (produto R$ %s, frete %s) "
                    "(tentativa %s)",
                    produto.id,
                    preco,
                    preco_produto,
                    "n/d" if frete is None else f"R$ {frete}",
                    tentativa,
                )
                return ResultadoColeta(
                    sucesso=True,
                    produto_id=produto.id,
                    preco=preco,
                    coleta_valida=True,
                    tentativas=tentativa,
                    historico_id=historico.id,
                    frete=frete,
                    preco_produto=preco_produto,
                )
=======
                preco = extrair_preco(resposta.text, dominio)
                if preco is None:
                    raise FalhaColeta(
                        MOTIVO_LAYOUT, _mensagem_layout_alterado(produto, loja, dominio)
                    )
>>>>>>> fc95810ab81209f9418926a060684f6f9af4bddb
            except Exception as exc:
                ultimo_erro = str(exc)
                ultimo_motivo = _classificar_falha(exc)
                logger.warning(
                    "Tentativa %s/%s falhou para o produto %s [%s]: %s",
                    tentativa,
                    max_tentativas,
                    produto.id,
                    ultimo_motivo,
                    ultimo_erro,
                )
                if _erro_nao_retriavel(exc):
                    return self._registrar_falha(
                        db,
                        produto,
                        tentativas=tentativa,
                        erro=ultimo_erro,
                        motivo=ultimo_motivo,
                    )
                # Não precisa esperar aqui: a próxima _requisitar já respeita o
                # intervalo mínimo (RNF08). Esperar nos dois lugares dobrava o tempo.
                continue

            return self._registrar_sucesso(db, produto, preco, tentativa)

        return self._registrar_falha(
            db,
            produto,
            tentativas=max_tentativas,
            erro=ultimo_erro,
            motivo=ultimo_motivo,
        )

    def _registrar_sucesso(
        self, db: Session, produto: Produto, preco: Decimal, tentativa: int
    ) -> ResultadoColeta:
        """Grava a coleta válida. Falha de banco vira coleta inválida, não exceção."""
        produto_id = produto.id
        url_produto = produto.url_produto  # lido já: depois de um rollback o objeto expira
        try:
            historico = HistoricoPreco(
                produto_id=produto_id,
                preco=preco,
                coleta_valida=True,
            )
            db.add(historico)
            db.commit()
            db.refresh(historico)
        except Exception as exc:
            _rollback_seguro(db)
            logger.exception(
                "Preço R$ %s do produto %s extraído, mas não foi possível gravar.",
                preco,
                produto_id,
            )
            return self._registrar_falha(
                db,
                produto,
                tentativas=tentativa,
                # Só o tipo do erro: a mensagem do driver traz host/usuário do banco.
                erro=f"Preço extraído, mas não foi possível gravar no banco ({type(exc).__name__}).",
                motivo=MOTIVO_BANCO,
                produto_id=produto_id,
                url=url_produto,
            )
        logger.info(
            "Coleta válida do produto %s: R$ %s (tentativa %s)",
            produto_id,
            preco,
            tentativa,
        )
        return ResultadoColeta(
            sucesso=True,
            produto_id=produto_id,
            preco=preco,
            coleta_valida=True,
            tentativas=tentativa,
            historico_id=historico.id,
        )

    @staticmethod
    def _extrair_frete_seguro(html: str) -> Optional[Decimal]:
        if not settings.COLETA_INCLUIR_FRETE:
            return None
        try:
            return extrair_frete(html)
        except Exception:
            logger.warning("Não foi possível ler o frete da página.", exc_info=True)
            return None

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
        # Guarda os ids agora: depois de um commit/rollback os objetos expiram e
        # ler o id de novo iria ao banco (que pode ser justamente o que falhou).
        alvos = [(produto, produto.id) for produto in produtos]
        resultados: list[ResultadoColeta] = []
        for produto, produto_id in alvos:
            # RF08: a falha de um produto/loja nunca interrompe os demais.
            try:
                resultado = self.executar_coleta(produto, db)
            except Exception as exc:
                _rollback_seguro(db)
                logger.exception(
                    "Erro inesperado na coleta do produto %s; seguindo para o próximo.",
                    produto_id,
                )
                resultado = ResultadoColeta(
                    sucesso=False,
                    produto_id=produto_id,
                    preco=None,
                    coleta_valida=False,
                    tentativas=0,
                    erro=f"Erro inesperado na coleta ({type(exc).__name__}).",
                    motivo_falha=MOTIVO_INESPERADO,
                )
            resultados.append(resultado)
            if ao_coletar is not None:
                try:
                    ao_coletar(produto, resultado)
                except Exception:
                    _rollback_seguro(db)
                    logger.exception(
                        "Falha no pós-processamento do produto %s.", produto_id
                    )
        return resultados

    def _obter_pagina(self, url: str):
        """Busca a página (issue #103).

        - modo "desligado": só `requests`;
        - modo "auto": `requests` primeiro; se a loja bloquear, repete no Chrome
          (Selenium);
        - modo "sempre": só o Chrome.
        Se o Selenium/Chrome não estiver disponível, mantém o comportamento
        antigo (a resposta bloqueada vira falha de coleta, RN09).
        """
        modo = navegador.modo_selenium()
        if modo == navegador.MODO_SEMPRE:
            return self._requisitar_navegador(url)

        resposta = self._requisitar(url)
        if modo == navegador.MODO_AUTO and _precisa_navegador(resposta):
            logger.info("Loja bloqueou o requests em %s; tentando com Selenium.", url)
            try:
                return self._requisitar_navegador(url)
            except navegador.NavegadorIndisponivel as exc:
                logger.warning("Selenium indisponível (%s); mantendo a resposta original.", exc)
        return resposta

    def _requisitar_navegador(self, url: str):
        self._aguardar_intervalo()
        return navegador.buscar_pagina(url, USER_AGENT, _pagina_bloqueada)

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
        motivo: str = MOTIVO_INESPERADO,
        produto_id: Optional[UUID] = None,
        url: Optional[str] = None,
    ) -> ResultadoColeta:
        """Registra a falha sem apagar o histórico anterior e sem inventar preço.

        RN09/RN14: grava uma linha com `coleta_valida=False` e `preco=NULL`.
        Nunca 0.00 nem o último preço conhecido: a linha só marca que a coleta
        falhou. Se nem isso puder ser gravado, o erro é logado e a coleta segue
        sem exceção, para não derrubar os outros produtos.
        """
        if produto_id is None:
            produto_id = _id_sem_consulta(produto)
        if url is None:
            url = _url_sem_consulta(produto)
        historico_id = None
        try:
            historico = HistoricoPreco(
                produto_id=produto_id,
                preco=None,
                coleta_valida=False,
            )
            db.add(historico)
            db.commit()
            db.refresh(historico)
            historico_id = historico.id
        except Exception:
            _rollback_seguro(db)
            logger.exception(
                "Não foi possível registrar a falha de coleta do produto %s no histórico.",
                produto_id,
            )
        logger.error(
            "Coleta inválida do produto %s (%s) [%s] após %s tentativa(s): %s "
            "Histórico anterior preservado.",
            produto_id,
            url,
            motivo,
            tentativas,
            erro,
        )
        return ResultadoColeta(
            sucesso=False,
            produto_id=produto_id,
            preco=None,
            coleta_valida=False,
            tentativas=tentativas,
            historico_id=historico_id,
            erro=erro,
            motivo_falha=motivo,
        )
