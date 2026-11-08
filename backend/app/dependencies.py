import logging
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db, supabase
from app.models.usuario import Usuario
from app.utils.erros import eh_indisponibilidade

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False, description="Access token do Supabase Auth")


def _nao_autenticado(detalhe: str = "Autenticação necessária. Faça login novamente."):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalhe,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_usuario_atual(
    request: Request,
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Valida o token do Supabase e devolve o Usuario do domínio (RN02, RNF03).

    Falhas de autenticação são registradas (sem o token) com método, rota e IP.
    """
    origem = f"{request.method} {request.url.path} ip={request.client.host if request.client else '?'}"

    if credenciais is None:
        logger.warning("Falha de autenticação: requisição sem token. %s", origem)
        raise _nao_autenticado()

    try:
        resposta = supabase.auth.get_user(credenciais.credentials)
        auth_user = resposta.user if resposta else None
    except Exception as exc:
        if eh_indisponibilidade(exc):
            # Não é culpa do usuário: não derruba a sessão com um falso "expirou".
            logger.error(
                "Serviço de autenticação indisponível (%s). %s", type(exc).__name__, origem
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Serviço de autenticação indisponível no momento. Tente novamente em instantes.",
            )
        logger.warning("Falha de autenticação: token recusado (%s). %s", type(exc).__name__, origem)
        auth_user = None
    if auth_user is None:
        logger.warning("Falha de autenticação: sessão inválida ou expirada. %s", origem)
        raise _nao_autenticado("Sessão inválida ou expirada. Faça login novamente.")

    usuario = db.get(Usuario, uuid.UUID(str(auth_user.id)))
    if usuario is None:
        logger.warning(
            "Falha de autenticação: usuário %s existe no Auth mas não na tabela usuarios. %s",
            auth_user.id,
            origem,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro do usuário incompleto na plataforma.",
        )
    return usuario
