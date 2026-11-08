"""Configuração central de logs, com redação de segredos (RNF03).

Todo registro passa por `FiltroSegredos`, que troca senhas, tokens JWT,
cabeçalhos Bearer, chaves de API e senhas em URLs de conexão por `***` antes
de chegar ao console. Isso vale também para o traceback (`logger.exception`),
porque a mensagem de uma exceção pode carregar o que a causou.

Uso: `configurar_logging()` é chamada uma vez em app/main.py.
"""
from __future__ import annotations

import logging
import os
import re
import traceback

_PADROES: tuple[tuple[re.Pattern[str], str], ...] = (
    # senha=..., "senha": "...", token: ..., api_key=..., password=...
    (
        re.compile(
            r"""(?ix)
            (senha|password|passwd|pwd|secret|api[_-]?key|apikey|
             access[_-]?token|refresh[_-]?token|token)
            (["']?\s*[:=]\s*)(["']?)
            [^\s"',;&})\]]+
            """
        ),
        r"\1\2\3***",
    ),
    # Authorization: Bearer xxx
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1***"),
    # JWT solto (Supabase access/refresh token, service_role key)
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\.?[A-Za-z0-9_-]*"), "***jwt***"),
    # chaves novas do Supabase
    (re.compile(r"\b(sb_secret_|sb_publishable_)[A-Za-z0-9_-]+"), r"\1***"),
    # postgresql://usuario:SENHA@host/db
    (re.compile(r"((?:postgres(?:ql)?|mysql)(?:\+\w+)?://[^:/\s]+:)[^@\s]+@"), r"\1***@"),
)


def redigir(texto: str) -> str:
    """Remove segredos conhecidos de um texto."""
    for padrao, troca in _PADROES:
        texto = padrao.sub(troca, texto)
    return texto


class FiltroSegredos(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redigir(record.getMessage())
            record.args = None
            if record.exc_info and not record.exc_text:
                bruto = "".join(traceback.format_exception(*record.exc_info)).rstrip()
                record.exc_text = redigir(bruto)
        except Exception:  # log nunca pode derrubar a aplicação
            record.msg = "[registro omitido: falha ao redigir segredos]"
            record.args = None
            record.exc_info = None
        return True


_FORMATO = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configurar_logging() -> None:
    """Idempotente: pode ser chamada mais de uma vez sem duplicar handlers."""
    raiz = logging.getLogger()
    if not any(getattr(h, "_pricebrother", False) for h in raiz.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMATO))
        handler.addFilter(FiltroSegredos())
        handler._pricebrother = True  # type: ignore[attr-defined]
        raiz.addHandler(handler)
    raiz.setLevel(os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO")

    # O uvicorn tem handlers próprios; o filtro vai nos loggers dele para
    # cobrir também o traceback de erros não tratados.
    for nome in ("uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(nome)
        if not any(isinstance(f, FiltroSegredos) for f in lg.filters):
            lg.addFilter(FiltroSegredos())
