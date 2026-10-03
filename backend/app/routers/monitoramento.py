import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.monitoramento import MonitoramentoCreate, MonitoramentoUpdate
from app.schemas.produto import ProdutoMonitoradoOut

router = APIRouter(prefix="/monitoramentos", tags=["Monitoramento"])

_MSG_NAO_ENCONTRADO = "Monitoramento não encontrado."
_MSG_JA_MONITORA = "Você já está monitorando este produto."


def _montar_saida(produto: Produto, loja: Loja, mon: Monitoramento) -> ProdutoMonitoradoOut:
    return ProdutoMonitoradoOut(
        produto_id=produto.id,
        nome=produto.nome,
        url_produto=produto.url_produto,
        ativo=produto.ativo,
        loja=loja,
        monitoramento_id=mon.id,
        preco_alvo=mon.preco_alvo,
        alerta_ativo=mon.alerta_ativo,
        data_cadastro=mon.data_cadastro,
    )


def _buscar_do_usuario(db: Session, monitoramento_id: uuid.UUID, usuario_id: uuid.UUID) -> Monitoramento:
    monitoramento = db.get(Monitoramento, monitoramento_id)
    # RNF03: não revela se o monitoramento existe mas pertence a outro usuário.
    if monitoramento is None or monitoramento.usuario_id != usuario_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _MSG_NAO_ENCONTRADO)
    return monitoramento


@router.post(
    "",
    response_model=ProdutoMonitoradoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Vincular produto já cadastrado à lista de monitoramento (UC04)",
)
def criar_monitoramento(
    dados: MonitoramentoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    produto = db.get(Produto, dados.produto_id)
    if produto is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Produto não encontrado. Cadastre o produto antes de monitorá-lo.",
        )

    ja_existe = db.scalar(
        select(Monitoramento).where(
            Monitoramento.usuario_id == usuario.id,
            Monitoramento.produto_id == produto.id,
        )
    )
    if ja_existe is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, _MSG_JA_MONITORA)

    monitoramento = Monitoramento(
        usuario_id=usuario.id, produto_id=produto.id, preco_alvo=dados.preco_alvo
    )
    db.add(monitoramento)
    produto.ativo = True  # volta a ser coletado, caso estivesse sem nenhum monitoramento
    db.commit()
    db.refresh(monitoramento)
    db.refresh(produto)

    loja = db.get(Loja, produto.loja_id)
    return _montar_saida(produto, loja, monitoramento)


@router.patch(
    "/{monitoramento_id}",
    response_model=ProdutoMonitoradoOut,
    summary="Definir preço-alvo e ativar/desativar alertas (UC08)",
)
def atualizar_monitoramento(
    monitoramento_id: uuid.UUID,
    dados: MonitoramentoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    monitoramento = _buscar_do_usuario(db, monitoramento_id, usuario.id)

    campos_enviados = dados.model_fields_set
    if "preco_alvo" in campos_enviados:
        monitoramento.preco_alvo = dados.preco_alvo  # None limpa o preço-alvo (RN07)
    if "alerta_ativo" in campos_enviados and dados.alerta_ativo is not None:
        monitoramento.alerta_ativo = dados.alerta_ativo

    db.commit()
    db.refresh(monitoramento)

    produto = db.get(Produto, monitoramento.produto_id)
    loja = db.get(Loja, produto.loja_id)
    return _montar_saida(produto, loja, monitoramento)
