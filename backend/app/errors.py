"""Tratamento global de erros HTTP (RNF03): mensagens em português e sem
detalhes técnicos.

Problemas que isto resolve:
  * O 422 padrão do FastAPI vem em inglês ("Field required") e devolve o campo
    `input`, que em erro de campo ausente é o CORPO INTEIRO da requisição, o que
    inclui a senha digitada no cadastro e no login.
  * Exceção não tratada vira "Internal Server Error" em inglês.
  * 404/405 de rota inexistente também vêm em inglês.

A forma da resposta segue a dos demais erros da API (`{"detail": "texto"}`),
com a lista de campos em `erros` para o frontend destacar cada campo.
"""
from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.erros")

MSG_ERRO_INTERNO = "Ocorreu um erro interno. Tente novamente em instantes."

_NOMES_CAMPOS = {
    "nome": "nome",
    "email": "e-mail",
    "senha": "senha",
    "url_produto": "URL do produto",
    "loja_id": "loja",
    "produto_id": "produto",
    "preco_alvo": "preço-alvo",
    "alerta_ativo": "alerta ativo",
    "dominio": "domínio",
    "janela_dias": "janela em dias",
    "limite": "limite",
    "monitoramento_id": "monitoramento",
}


def _traduzir(erro: dict) -> str:
    tipo = erro.get("type", "")
    ctx = erro.get("ctx") or {}
    msg = str(erro.get("msg", ""))

    if tipo == "missing":
        return "campo obrigatório."
    if tipo == "string_too_short":
        return f"deve ter ao menos {ctx.get('min_length', '?')} caracteres."
    if tipo == "string_too_long":
        return f"deve ter no máximo {ctx.get('max_length', '?')} caracteres."
    if tipo in {"greater_than", "greater_than_equal", "less_than", "less_than_equal"}:
        rotulo = {
            "greater_than": ("maior que", "gt"),
            "greater_than_equal": ("maior ou igual a", "ge"),
            "less_than": ("menor que", "lt"),
            "less_than_equal": ("menor ou igual a", "le"),
        }[tipo]
        return f"deve ser {rotulo[0]} {ctx.get(rotulo[1], '?')}."
    if tipo in {"uuid_parsing", "uuid_type", "uuid_version"}:
        return "identificador inválido."
    if tipo.startswith(("decimal_max", "decimal_whole")):
        return "valor com dígitos ou casas decimais demais."
    if tipo.startswith(("decimal_", "float_", "int_")):
        return "informe um número válido."
    if tipo.startswith("bool"):
        return "deve ser verdadeiro ou falso."
    if tipo.startswith("string_") or tipo == "string_type":
        return "texto inválido."
    if tipo == "value_error":
        # Mensagens dos nossos validadores já vêm em português ("Value error, <pt>").
        if "email" in msg.lower() and "valid" in msg.lower():
            return "e-mail inválido."
        limpo = msg.removeprefix("Value error, ").strip()
        # Só repassa se parecer texto nosso (tem acento ou termina com ponto e não é inglês técnico).
        if limpo and (
            any(c in limpo for c in "áàâãéêíóôõúçÁÉÍÓÚÇ")
            or limpo.startswith(("Informe", "O ", "A ", "Apenas"))
        ):
            return limpo if limpo.endswith(".") else limpo + "."
        return "valor inválido."
    return "valor inválido."


def _montar_erros(exc: RequestValidationError) -> list[dict]:
    saida = []
    for erro in exc.errors():
        loc = [p for p in erro.get("loc", ()) if p not in ("body", "query", "path")]
        bruto = str(loc[-1]) if loc else ""
        campo = _NOMES_CAMPOS.get(bruto, bruto) if not bruto.isdigit() else ""
        if erro.get("type") == "json_invalid":
            saida.append({"campo": "", "mensagem": "O corpo da requisição não é um JSON válido."})
            continue
        saida.append({"campo": campo, "mensagem": _traduzir(erro)})
    return saida


def _resumo(erros: list[dict]) -> str:
    partes = []
    for e in erros:
        partes.append(f"{e['campo']}: {e['mensagem']}" if e["campo"] else e["mensagem"])
    return "Dados inválidos. " + " ".join(partes) if partes else "Dados inválidos."


_MSG_HTTP = {
    404: "Recurso não encontrado.",
    405: "Método não permitido para este recurso.",
    401: "Autenticação necessária. Faça login novamente.",
    403: "Você não tem permissão para esta ação.",
    429: "Muitas requisições. Aguarde um instante e tente novamente.",
}


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validacao(request: Request, exc: RequestValidationError):
        erros = _montar_erros(exc)
        # Nunca registra nem devolve `input`: pode conter senha.
        logger.info(
            "Validação recusada em %s %s: campos=%s",
            request.method,
            request.url.path,
            [e["campo"] or "corpo" for e in erros],
        )
        return JSONResponse(status_code=422, content={"detail": _resumo(erros), "erros": erros})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        detalhe = exc.detail
        try:
            padrao_ingles = HTTPStatus(exc.status_code).phrase
        except ValueError:
            padrao_ingles = ""
        if not isinstance(detalhe, str) or not detalhe or detalhe == padrao_ingles:
            detalhe = _MSG_HTTP.get(exc.status_code, "Não foi possível concluir a requisição.")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detalhe},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception):
        # O traceback fica só no log (já sem segredos); o usuário vê texto genérico.
        logger.error(
            "Erro não tratado em %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(status_code=500, content={"detail": MSG_ERRO_INTERNO})
