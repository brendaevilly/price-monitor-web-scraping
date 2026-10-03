
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db, supabase
from app.models.usuario import Usuario
from app.schemas.usuario import LoginOut, UsuarioCreate, UsuarioLogin, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuario"])

_MSG_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."


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


@router.post(
    "/login",
    response_model=LoginOut,
    status_code=status.HTTP_200_OK,
    summary="Realizar login (UC02)",
)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    email_normalizado = dados.email.lower()

    # 1-2. Sistema valida as credenciais junto ao Supabase Auth.
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": email_normalizado, "password": dados.senha}
        )
    except Exception as exc:
        mensagem = str(exc).lower()
        if "email not confirmed" in mensagem:
            # Variante de credenciais ainda não utilizáveis: conta existe, mas
            # o e-mail não foi confirmado. Mensagem específica ajuda o usuário
            # a saber o que fazer, sem revelar se o e-mail está cadastrado.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="E-mail ainda não confirmado. Verifique sua caixa de entrada.",
            )
        # 2a. Credenciais inválidas (e-mail ou senha incorretos).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MSG_CREDENCIAIS_INVALIDAS,
        )

    sessao = auth_response.session
    auth_user = auth_response.user
    if sessao is None or auth_user is None:
        # 2a. Supabase não recusou explicitamente, mas também não autenticou.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MSG_CREDENCIAIS_INVALIDAS,
        )

    # 3. Sistema concede acesso à área restrita: usuário correspondente no
    # domínio da aplicação (tabela usuarios), não só no Supabase Auth.
    usuario = db.get(Usuario, auth_user.id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadastro do usuário incompleto na plataforma.",
        )

    return LoginOut(
        access_token=sessao.access_token,
        refresh_token=sessao.refresh_token,
        expires_in=sessao.expires_in,
        usuario=UsuarioOut(
            id=usuario.id,
            nome=usuario.nome,
            email=email_normalizado,
            criado_em=usuario.criado_em,
        ),
    )