"""Utilitários de tratamento de erro e de privacidade em logs (RNF03).

Funções puras, sem dependência de banco ou HTTP, para poderem ser testadas
isoladamente e reaproveitadas por routers, dependências e serviços.
"""
from __future__ import annotations

import httpx


def eh_indisponibilidade(exc: BaseException) -> bool:
    """True quando o erro indica serviço externo fora do ar (rede, DNS, timeout).

    Serve para diferenciar "o Supabase não respondeu" (503, culpa da infra) de
    "o token/senha foi recusado" (401, culpa do usuário). Sem essa distinção,
    uma queda do Supabase aparece para o usuário como "senha incorreta" ou
    como "sessão expirada".
    """
    return isinstance(exc, (httpx.TransportError, ConnectionError, TimeoutError, OSError))


def mascarar_email(email: str | None) -> str:
    """'ana.silva@gmail.com' -> 'an***@gmail.com' (identifica sem expor por inteiro)."""
    if not email or "@" not in email:
        return "***"
    local, _, dominio = email.partition("@")
    return f"{local[:2]}***@{dominio}"
