
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db, supabase
from app.models.usuario import Usuario
from app.schemas.usuario import LoginOut, UsuarioCreate, UsuarioLogin, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuario"])
logger = logging.getLogger(__name__)

_MSG_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."
_MSG_EMAIL_DUPLICADO = "Já existe um usuário cadastrado com este e-mail."
_MSG_EMAIL_NAO_CONFIRMADO = (
    "E-mail ainda não confirmado. Verifique sua caixa de entrada "
    "ou desative 'Confirm email' no Supabase (Authentication > Providers > Email)."
)


def _conflito_email() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=_MSG_EMAIL_DUPLICADO,
    )


def _salvar_usuario_dominio(db: Session, user_id, nome: str) -> Usuario:
    existente = db.get(Usuario, user_id)
    if existente is not None:
        raise _conflito_email()
    novo = Usuario(id=user_id, nome=nome)
    db.add(novo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _conflito_email()
    db.refresh(novo)
    return novo


def _confirmar_email(user_id) -> None:
    try:
        supabase.auth.admin.update_user_by_id(str(user_id), {"email_confirm": True})
    except Exception as exc:
        logger.warning("Não foi possível confirmar e-mail no Auth: %s", exc)


def _buscar_auth_por_email(email: str):
    try:
        resposta = supabase.auth.admin.list_users()
    except Exception as exc:
        logger.warning("list_users falhou: %s", exc)
        return None
    users = getattr(resposta, "users", None)
    if not isinstance(users, (list, tuple)):
        return None
    for user in users:
        if str(getattr(user, "email", "")).lower() == email:
            return user
    return None


def _criar_no_auth(email: str, senha: str):
    """Cria no Auth já confirmado (MVP). Se o e-mail existir, devolve o usuário."""
    try:
        resposta = supabase.auth.admin.create_user(
            {
                "email": email,
                "password": senha,
                "email_confirm": True,
            }
        )
        user = getattr(resposta, "user", None) or resposta
        if user is not None and getattr(user, "id", None):
            return user
    except Exception as exc:
        mensagem = str(exc).lower()
        if "invalid" in mensagem and "email" in mensagem:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="E-mail inválido.",
            )
        if "already" in mensagem or "registered" in mensagem or "exists" in mensagem:
            existente = _buscar_auth_por_email(email)
            if existente is not None:
                _confirmar_email(existente.id)
                return existente
            raise _conflito_email()
        logger.exception("Falha ao criar usuário no Supabase Auth")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao cadastrar no Supabase Auth: {exc}",
        )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Supabase Auth não retornou o usuário criado.",
    )


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário (UC01)",
)
def cadastrar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    email_normalizado = dados.email.lower()
    auth_user = _criar_no_auth(email_normalizado, dados.senha)
    novo_usuario = _salvar_usuario_dominio(db, auth_user.id, dados.nome)
    return UsuarioOut(
        id=novo_usuario.id,
        nome=novo_usuario.nome,
        email=email_normalizado,
        criado_em=novo_usuario.criado_em,
    )


def _entrar(email: str, senha: str):
    return supabase.auth.sign_in_with_password({"email": email, "password": senha})


@router.post(
    "/login",
    response_model=LoginOut,
    status_code=status.HTTP_200_OK,
    summary="Realizar login (UC02)",
)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    email_normalizado = dados.email.lower()

    try:
        auth_response = _entrar(email_normalizado, dados.senha)
    except Exception as exc:
        mensagem = str(exc).lower()
        auth_existente = _buscar_auth_por_email(email_normalizado)
        confirmado = bool(getattr(auth_existente, "email_confirmed_at", None)) if auth_existente else True
        if auth_existente is not None and not confirmado:
            _confirmar_email(auth_existente.id)
            try:
                auth_response = _entrar(email_normalizado, dados.senha)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=_MSG_EMAIL_NAO_CONFIRMADO,
                )
        elif "email not confirmed" in mensagem:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_MSG_EMAIL_NAO_CONFIRMADO,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=_MSG_CREDENCIAIS_INVALIDAS,
            )

    sessao = auth_response.session
    auth_user = auth_response.user
    if sessao is None or auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_MSG_CREDENCIAIS_INVALIDAS,
        )

    usuario = db.get(Usuario, auth_user.id)
    if usuario is None:
        try:
            usuario = db.get(Usuario, UUID(str(auth_user.id)))
        except (TypeError, ValueError):
            usuario = None
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
