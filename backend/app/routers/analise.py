import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.models.historico_preco import HistoricoPreco
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.models.usuario import Usuario
from app.routers.produto import _analise_service, _duas_casas
from app.schemas.analise import ResumoAnaliseOut, ResumoProdutoOut
from app.services.analise_service import ClassificacaoQueda

router = APIRouter(prefix="/analise", tags=["Análise"])


def _pct(v: float | None) -> float | None:
    return None if v is None else round(v, 2)


@router.get(
    "/resumo",
    response_model=ResumoAnaliseOut,
    summary="Resumo da análise de todos os meus produtos (UC11, RNF03)",
)
def resumo_analise(
    janela_dias: int | None = Query(
        default=None,
        ge=0,
        le=3650,
        description="Janela da média em dias (0 = todo o histórico). Omitido: usa ANALISE_JANELA_DIAS.",
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    janela = _analise_service.janela_dias if janela_dias is None else janela_dias

    # RNF03: só os produtos que o usuário autenticado monitora.
    produtos = db.scalars(
        select(Produto)
        .join(Monitoramento, Monitoramento.produto_id == Produto.id)
        .where(Monitoramento.usuario_id == usuario.id)
        .order_by(Monitoramento.data_cadastro.desc())
    ).all()

    # RNF01: uma única consulta traz as coletas de todos os produtos (sem N+1).
    # RN09: só coletas válidas; o agrupamento por produto_id garante que cada
    # análise use apenas coletas do próprio produto (RN10).
    por_produto: dict[uuid.UUID, list] = defaultdict(list)
    if produtos:
        linhas = db.execute(
            select(
                HistoricoPreco.produto_id,
                HistoricoPreco.preco,
                HistoricoPreco.data_hora_coleta,
                HistoricoPreco.coleta_valida,
            )
            .where(
                HistoricoPreco.produto_id.in_([p.id for p in produtos]),
                HistoricoPreco.coleta_valida.is_(True),
            )
            .order_by(HistoricoPreco.produto_id, HistoricoPreco.data_hora_coleta.asc())
        ).all()
        for linha in linhas:
            por_produto[linha.produto_id].append(linha)

    itens: list[ResumoProdutoOut] = []
    for produto in produtos:
        coletas = por_produto.get(produto.id, [])
        if not coletas:
            # Sem coleta válida: sem_dados, não classifica queda.
            itens.append(ResumoProdutoOut(
                produto_id=produto.id, nome=produto.nome, url_produto=produto.url_produto,
                preco_atual=None, menor_preco=None, media_historica=None, amostras_media=0,
                variacao_percentual_anterior=None, variacao_percentual_media=None,
                classificacao=ClassificacaoQueda.SEM_DADOS, queda_relevante=False,
            ))
            continue
        r = _analise_service.classificar(coletas, janela_dias=janela)
        itens.append(ResumoProdutoOut(
            produto_id=produto.id, nome=produto.nome, url_produto=produto.url_produto,
            preco_atual=_duas_casas(r.preco_atual),
            menor_preco=_duas_casas(min(c.preco for c in coletas)),
            media_historica=_duas_casas(r.media_historica),
            amostras_media=r.amostras_media,
            variacao_percentual_anterior=_pct(r.variacao_percentual_anterior),
            variacao_percentual_media=_pct(r.variacao_percentual_media),
            classificacao=r.classificacao, queda_relevante=r.queda_relevante,
        ))

    contagem = {c: 0 for c in ClassificacaoQueda}
    for item in itens:
        contagem[item.classificacao] += 1

    return ResumoAnaliseOut(
        janela_dias=janela,
        amostras_minimas=_analise_service.min_amostras_media,
        total_produtos=len(itens),
        contagem_por_classificacao=contagem,
        produtos=itens,
    )
