
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db, supabase
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuario"])


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário (UC01)",
)
def cadastrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    email_normalizado = dados.email.lower()

    # 1. Cria o usuário no Supabase Auth (ele valida e-mail/senha e cuida do hash).
    try:
        auth_response = supabase.auth.sign_up(
            {"email": email_normalizado, "password": dados.senha}
        )
    except Exception as exc:
        mensagem = str(exc).lower()
        if "already registered" in mensagem or "already exists" in mensagem:
            # 3a. E-mail já cadastrado
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário cadastrado com este e-mail.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao cadastrar no Supabase Auth: {exc}",
        )

    auth_user = auth_response.user
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase Auth não retornou o usuário criado.",
        )

    novo_usuario = Usuario(id=auth_user.id, nome=dados.nome)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return UsuarioOut(
        id=novo_usuario.id,
        nome=novo_usuario.nome,
        email=email_normalizado,
        criado_em=novo_usuario.criado_em,
    )