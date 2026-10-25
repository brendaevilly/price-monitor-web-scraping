import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.schemas.analise import AnaliseProdutoOut
from app.schemas.historico import ColetaPrecoOut, HistoricoProdutoOut
from app.schemas.produto import ProdutoCreate, ProdutoMonitoradoOut
from app.services.analise_service import AnaliseService, ClassificacaoQueda
from app.utils.urls import url_pertence_a_loja

router = APIRouter(prefix="/produtos", tags=["Produto"])

_MSG_NAO_ENCONTRADO = "Produto não encontrado."

# RNF07: serviço sem estado de negócio, pode ser reaproveitado entre requisições.
_analise_service = AnaliseService()


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


def _duas_casas(valor: Decimal | None) -> Decimal | None:
    if valor is None:
        return None
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _produto_monitorado_pelo_usuario(db: Session, produto_id: uuid.UUID, usuario: Usuario) -> Produto:
    """RNF03: só dá acesso a produtos que o usuário monitora; não revela se o
    produto existe mas é monitorado só por outra pessoa."""
    produto = db.get(Produto, produto_id)
    monitora = db.scalar(
        select(Monitoramento).where(
            Monitoramento.usuario_id == usuario.id,
            Monitoramento.produto_id == produto_id,
        )
    )
    if produto is None or monitora is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _MSG_NAO_ENCONTRADO)
    return produto


def _coletas_validas(db: Session, produto_id: uuid.UUID) -> list[HistoricoPreco]:
    """RN09: só coletas deste produto (nunca mistura com outro) e só válidas,
    da mais antiga para a mais recente."""
    return list(
        db.scalars(
            select(HistoricoPreco)
            .where(
                HistoricoPreco.produto_id == produto_id,
                HistoricoPreco.coleta_valida.is_(True),
            )
            .order_by(HistoricoPreco.data_hora_coleta.asc())
        ).all()
    )


@router.get(
    "/{produto_id}/historico",
    response_model=HistoricoProdutoOut,
    summary="Consultar histórico de preços do produto (RF12, RN09, RN10)",
)
def consultar_historico(
    produto_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    produto = _produto_monitorado_pelo_usuario(db, produto_id, usuario)
    coletas = _coletas_validas(db, produto_id)

    if not coletas:
        return HistoricoProdutoOut(
            produto_id=produto.id,
            nome=produto.nome,
            url_produto=produto.url_produto,
            coletas=[],
            preco_atual=None,
            menor_preco=None,
            media_historica=None,
            amostras_media=0,
        )

    # RN10: a média só vem preenchida quando há amostras suficientes (mesmo
    # critério da análise de quedas, UC11).
    resultado = _analise_service.classificar(coletas)

    return HistoricoProdutoOut(
        produto_id=produto.id,
        nome=produto.nome,
        url_produto=produto.url_produto,
        coletas=[ColetaPrecoOut.model_validate(c) for c in coletas],
        preco_atual=resultado.preco_atual,
        menor_preco=min(c.preco for c in coletas),
        media_historica=_duas_casas(resultado.media_historica),
        amostras_media=resultado.amostras_media,
    )


@router.get(
    "/{produto_id}/analise",
    response_model=AnaliseProdutoOut,
    summary="Analisar variação de preço e classificar queda (UC11, RN10)",
)
def analisar_produto(
    produto_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    produto = _produto_monitorado_pelo_usuario(db, produto_id, usuario)
    coletas = _coletas_validas(db, produto_id)
    minimo = _analise_service.min_amostras_media

    if not coletas:
        # Sem nenhuma coleta válida não há o que comparar: não classifica (UC11, 3a).
        return AnaliseProdutoOut(
            produto_id=produto.id,
            nome=produto.nome,
            preco_atual=None,
            media_historica=None,
            amostras_media=0,
            amostras_minimas=minimo,
            variacao_percentual_anterior=None,
            variacao_percentual_media=None,
            classificacao=ClassificacaoQueda.SEM_DADOS,
            queda_relevante=False,
        )

    # RN10: sem amostras suficientes o serviço devolve SEM_DADOS (não classifica queda).
    r = _analise_service.classificar(coletas)

    def _pct(v: float | None) -> float | None:
        return None if v is None else round(v, 2)

    return AnaliseProdutoOut(
        produto_id=produto.id,
        nome=produto.nome,
        preco_atual=_duas_casas(r.preco_atual),
        media_historica=_duas_casas(r.media_historica),
        amostras_media=r.amostras_media,
        amostras_minimas=minimo,
        variacao_percentual_anterior=_pct(r.variacao_percentual_anterior),
        variacao_percentual_media=_pct(r.variacao_percentual_media),
        classificacao=r.classificacao,
        queda_relevante=r.queda_relevante,
    )
