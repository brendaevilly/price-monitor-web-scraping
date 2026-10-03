from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.loja import Loja
from app.models.usuario import Usuario
from app.schemas.loja import LojaCreate, LojaOut

router = APIRouter(prefix="/lojas", tags=["Loja"])

_MSG_DUPLICADA = "Já existe uma loja cadastrada com este domínio."


@router.post(
    "",
    response_model=LojaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar loja",
)
def cadastrar_loja(
    dados: LojaCreate,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_usuario_atual),
):
    # O domínio já chega normalizado (minúsculo, sem www/caminho) pelo schema.
    if db.scalar(select(Loja).where(Loja.dominio == dados.dominio)):
        raise HTTPException(status.HTTP_409_CONFLICT, _MSG_DUPLICADA)

    loja = Loja(nome=dados.nome, dominio=dados.dominio)
    db.add(loja)
    try:
        db.commit()
    except IntegrityError:  # corrida entre duas requisições simultâneas
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, _MSG_DUPLICADA)
    db.refresh(loja)
    return loja


@router.get("", response_model=list[LojaOut], summary="Listar lojas")
def listar_lojas(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(get_usuario_atual),
):
    return db.scalars(select(Loja).order_by(Loja.nome)).all()
