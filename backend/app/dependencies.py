import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db, supabase
from app.models.usuario import Usuario

_bearer = HTTPBearer(auto_error=False, description="Access token do Supabase Auth")


def _nao_autenticado(detalhe: str = "Autenticação necessária. Faça login novamente."):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalhe,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Valida o token do Supabase e devolve o Usuario do domínio (RN02, RNF03)."""
    if credenciais is None:
        raise _nao_autenticado()

    try:
        resposta = supabase.auth.get_user(credenciais.credentials)
        auth_user = resposta.user if resposta else None
    except Exception:
        auth_user = None
    if auth_user is None:
        raise _nao_autenticado("Sessão inválida ou expirada. Faça login novamente.")

    usuario = db.get(Usuario, uuid.UUID(str(auth_user.id)))
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro do usuário incompleto na plataforma.",
        )
    return usuario
