from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.produto import ProdutoCreate, ProdutoMonitoradoOut
from app.utils.urls import url_pertence_a_loja

router = APIRouter(prefix="/produtos", tags=["Produto"])


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


@router.post(
    "",
    response_model=ProdutoMonitoradoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar produto monitorado (UC04, RF04, RF05, RN03)",
)
def cadastrar_produto(
    dados: ProdutoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    # Formato da URL, nome e preço-alvo já foram validados pelo schema (RF05).

    # RN03: a loja precisa existir...
    loja = db.get(Loja, dados.loja_id)
    if loja is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Loja não encontrada. Cadastre a loja antes de cadastrar o produto.",
        )
    # ...e a URL precisa pertencer a ela (é isso que "identifica" a loja do produto).
    if not url_pertence_a_loja(dados.url_produto, loja.dominio):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"A URL informada não pertence à loja '{loja.nome}' ({loja.dominio}).",
        )

    # O Produto é compartilhado entre usuários (o histórico é por produto, RN10):
    # se a URL já existe, reaproveita; só o Monitoramento é individual.
    produto = db.scalar(select(Produto).where(Produto.url_produto == dados.url_produto))
    if produto is None:
        produto = Produto(nome=dados.nome, url_produto=dados.url_produto, loja_id=loja.id)
        db.add(produto)
        db.flush()  # gera o id sem fechar a transação
    else:
        if db.scalar(
            select(Monitoramento).where(
                Monitoramento.usuario_id == usuario.id,
                Monitoramento.produto_id == produto.id,
            )
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Você já está monitorando este produto."
            )
        produto.ativo = True  # volta a ser coletado se estava sem monitoramento

    monitoramento = Monitoramento(
        usuario_id=usuario.id, produto_id=produto.id, preco_alvo=dados.preco_alvo
    )
    db.add(monitoramento)
    db.commit()  # Produto + Monitoramento salvos juntos ou nenhum
    db.refresh(produto)
    db.refresh(monitoramento)
    return _montar_saida(produto, loja, monitoramento)


@router.get("", response_model=list[ProdutoMonitoradoOut], summary="Listar meus produtos (UC06)")
def listar_produtos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    # RNF03: só devolve o que pertence ao usuário autenticado.
    linhas = db.execute(
        select(Produto, Loja, Monitoramento)
        .join(Monitoramento, Monitoramento.produto_id == Produto.id)
        .join(Loja, Loja.id == Produto.loja_id)
        .where(Monitoramento.usuario_id == usuario.id)
        .order_by(Monitoramento.data_cadastro.desc())
    ).all()
    return [_montar_saida(p, l, m) for p, l, m in linhas]
