"""Normalização e validação de domínios e URLs (RF05, RN03).

Funções puras (sem banco/HTTP) para poderem ser testadas isoladamente e
reaproveitadas pelo robô de coleta.
"""
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

MAX_URL = 2048
PORTAS_PERMITIDAS = {None, 80, 443}

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_TLD = re.compile(r"^([a-z]{2,63}|xn--[a-z0-9-]{1,59})$")
_SUFIXOS_INTERNOS = (".localhost", ".local", ".internal", ".lan", ".home")


class URLInvalida(ValueError):
    """Erro de validação com mensagem já pronta para o usuário (em português)."""


def _eh_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _validar_host(host: str | None) -> str:
    """Garante que o host é um domínio público plausível e o devolve normalizado."""
    if not host:
        raise URLInvalida("Não foi possível identificar o domínio.")
    host = host.strip().lower().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")  # suporta domínios com acento
    except UnicodeError:
        raise URLInvalida("O domínio informado é inválido.")

    if _eh_ip(host):
        raise URLInvalida("Endereços IP não são aceitos; informe o domínio da loja.")
    if host == "localhost" or host.endswith(_SUFIXOS_INTERNOS):
        raise URLInvalida("Apenas endereços públicos de lojas são aceitos.")

    partes = host.split(".")
    if len(host) > 253 or len(partes) < 2:
        raise URLInvalida("O domínio informado é inválido (ex.: minhaloja.com.br).")
    if not all(_LABEL.match(p) for p in partes) or not _TLD.match(partes[-1]):
        raise URLInvalida("O domínio informado é inválido (ex.: minhaloja.com.br).")
    return host


def _sem_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def normalizar_dominio(valor: str) -> str:
    """'https://www.Loja.com.br/x' -> 'loja.com.br' (aceita domínio puro ou URL)."""
    valor = (valor or "").strip().lower()
    if not valor:
        raise URLInvalida("O domínio da loja é obrigatório.")
    try:
        partes = urlsplit(valor if "://" in valor else f"//{valor}")
        host = partes.hostname
    except ValueError:
        raise URLInvalida("O domínio informado é inválido.")
    return _sem_www(_validar_host(host))


def normalizar_url_produto(valor: str) -> str:
    """Valida a URL de uma página de produto e devolve sua forma canônica."""
    valor = (valor or "").strip()
    if not valor:
        raise URLInvalida("A URL do produto é obrigatória.")
    if len(valor) > MAX_URL:
        raise URLInvalida("A URL do produto é longa demais.")

    try:
        partes = urlsplit(valor)
        porta = partes.port
        host = partes.hostname
    except ValueError:
        raise URLInvalida("A URL informada é inválida.")

    if partes.scheme.lower() not in ("http", "https"):
        raise URLInvalida("A URL deve começar com http:// ou https://.")
    if partes.username or partes.password:
        raise URLInvalida("A URL não pode conter usuário ou senha.")
    if porta not in PORTAS_PERMITIDAS:
        raise URLInvalida("A URL usa uma porta não permitida.")
    host = _validar_host(host)

    # RN03: precisa ser a página de um produto, não a home da loja.
    if partes.path in ("", "/") and not partes.query:
        raise URLInvalida("Informe a URL da página do produto, não a página inicial da loja.")

    # Remove o fragmento (#...) que não muda a página; mantém a query (pode ter variação/SKU).
    return urlunsplit((partes.scheme.lower(), host, partes.path or "/", partes.query, ""))


def extrair_dominio(url: str) -> str:
    """Domínio (sem 'www.') de uma URL já normalizada."""
    return _sem_www(urlsplit(url).hostname or "")


def url_pertence_a_loja(url: str, dominio_loja: str) -> bool:
    """True se a URL é do domínio da loja ou de um subdomínio dele."""
    host = extrair_dominio(url)
    dominio_loja = _sem_www(dominio_loja.lower())
    return host == dominio_loja or host.endswith("." + dominio_loja)
