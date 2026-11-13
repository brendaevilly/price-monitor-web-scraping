import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Row, select
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
from app.schemas.comparativo import ComparativoLojasOut, OfertaLojaOut
from app.schemas.produto import MAX_OUTRAS_LOJAS, OfertaLojaCreate, ProdutoCreate, ProdutoMonitoradoOut
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
        grupo_id=produto.grupo_id,
        monitoramento_id=mon.id,
        preco_alvo=mon.preco_alvo,
        alerta_ativo=mon.alerta_ativo,
        data_cadastro=mon.data_cadastro,
    )


def _loja_valida_para_url(db: Session, loja_id: uuid.UUID, url_produto: str) -> Loja:
    """RN03: a loja precisa existir e a URL precisa pertencer a ela."""
    loja = db.get(Loja, loja_id)
    if loja is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Loja não encontrada. Cadastre a loja antes de cadastrar o produto.",
        )
    # A URL é o que "identifica" a loja do produto.
    if not url_pertence_a_loja(url_produto, loja.dominio):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"A URL informada não pertence à loja '{loja.nome}' ({loja.dominio}).",
        )
    return loja


def _vincular_produto(
    db: Session,
    usuario: Usuario,
    *,
    nome: str,
    loja: Loja,
    url_produto: str,
    preco_alvo: Decimal | None,
    grupo_id: uuid.UUID | None = None,
) -> tuple[Produto, Monitoramento]:
    """Cria (ou reaproveita) o Produto da URL e o Monitoramento do usuário.

    Não faz commit: quem chama decide, para salvar tudo junto ou nada.
    """
    # O Produto é compartilhado entre usuários (o histórico é por produto, RN10):
    # se a URL já existe, reaproveita; só o Monitoramento é individual.
    produto = db.scalar(select(Produto).where(Produto.url_produto == url_produto))
    if produto is None:
        produto = Produto(nome=nome, url_produto=url_produto, loja_id=loja.id, grupo_id=grupo_id)
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
        if grupo_id is not None:
            if produto.grupo_id not in (None, grupo_id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"O produto da loja '{loja.nome}' já faz parte de outro grupo de lojas.",
                )
            produto.grupo_id = grupo_id
        produto.ativo = True  # volta a ser coletado se estava sem monitoramento

    monitoramento = Monitoramento(usuario_id=usuario.id, produto_id=produto.id, preco_alvo=preco_alvo)
    db.add(monitoramento)
    db.flush()
    return produto, monitoramento


def _ofertas_monitoradas(
    db: Session, usuario: Usuario, produto: Produto
) -> list[tuple[Produto, Loja, Monitoramento]]:
    """Ofertas do mesmo item (mesmo grupo) que o usuário monitora. Inclui o próprio produto."""
    filtro = Produto.grupo_id == produto.grupo_id if produto.grupo_id else Produto.id == produto.id
    return list(
        db.execute(
            select(Produto, Loja, Monitoramento)
            .join(Monitoramento, Monitoramento.produto_id == Produto.id)
            .join(Loja, Loja.id == Produto.loja_id)
            .where(filtro, Monitoramento.usuario_id == usuario.id)
            .order_by(Monitoramento.data_cadastro.asc())
        ).all()
    )


def _exigir_lojas_distintas(loja_ids: list[uuid.UUID]) -> None:
    if len(set(loja_ids)) != len(loja_ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Cada loja só pode aparecer uma vez por produto.",
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
    loja = _loja_valida_para_url(db, dados.loja_id, dados.url_produto)

    # Issue #104: o mesmo produto em outras lojas, tudo na mesma transação.
    extras = [(o, _loja_valida_para_url(db, o.loja_id, o.url_produto)) for o in dados.outras_lojas]
    _exigir_lojas_distintas([loja.id, *[l.id for _, l in extras]])
    grupo_id = uuid.uuid4() if extras else None

    try:
        produto, monitoramento = _vincular_produto(
            db, usuario, nome=dados.nome, loja=loja, url_produto=dados.url_produto,
            preco_alvo=dados.preco_alvo,
        )
        if grupo_id is not None:
            if produto.grupo_id not in (None, grupo_id):
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Este produto já faz parte de outro grupo de lojas."
                )
            produto.grupo_id = grupo_id
            for oferta, loja_extra in extras:
                _vincular_produto(
                    db, usuario, nome=oferta.nome or dados.nome, loja=loja_extra,
                    url_produto=oferta.url_produto,
                    preco_alvo=oferta.preco_alvo if oferta.preco_alvo is not None else dados.preco_alvo,
                    grupo_id=grupo_id,
                )
    except HTTPException:
        db.rollback()  # nada fica salvo se qualquer loja falhar
        raise

    db.commit()  # Produto(s) + Monitoramento(s) salvos juntos ou nenhum
    db.refresh(produto)
    db.refresh(monitoramento)
    return _montar_saida(produto, loja, monitoramento)


@router.post(
    "/{produto_id}/lojas",
    response_model=ProdutoMonitoradoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Monitorar o mesmo produto em mais uma loja (issue #104)",
)
def adicionar_loja(
    produto_id: uuid.UUID,
    dados: OfertaLojaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    origem = _produto_monitorado_pelo_usuario(db, produto_id, usuario)
    loja = _loja_valida_para_url(db, dados.loja_id, dados.url_produto)

    existentes = _ofertas_monitoradas(db, usuario, origem)
    if len(existentes) > MAX_OUTRAS_LOJAS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Limite de {MAX_OUTRAS_LOJAS + 1} lojas por produto atingido.",
        )
    if loja.id in {p.loja_id for p, _, _ in existentes}:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Você já monitora este produto na loja '{loja.nome}'."
        )

    grupo_id = origem.grupo_id or uuid.uuid4()
    monitoramento_origem = next(m for p, _, m in existentes if p.id == origem.id)
    try:
        produto, monitoramento = _vincular_produto(
            db, usuario, nome=dados.nome or origem.nome, loja=loja, url_produto=dados.url_produto,
            preco_alvo=dados.preco_alvo if dados.preco_alvo is not None else monitoramento_origem.preco_alvo,
            grupo_id=grupo_id,
        )
    except HTTPException:
        db.rollback()
        raise
    origem.grupo_id = grupo_id
    db.commit()
    db.refresh(produto)
    db.refresh(monitoramento)
    return _montar_saida(produto, loja, monitoramento)


@router.get(
    "/{produto_id}/lojas",
    response_model=ComparativoLojasOut,
    summary="Comparar o produto entre as lojas monitoradas (issue #104)",
)
def comparar_lojas(
    produto_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    produto = _produto_monitorado_pelo_usuario(db, produto_id, usuario)

    ofertas: list[OfertaLojaOut] = []
    for oferta, loja, _mon in _ofertas_monitoradas(db, usuario, produto):
        validas = _coletas_validas(db, oferta.id)  # RN09: só coletas válidas deste produto
        ultima = validas[-1] if validas else None
        ofertas.append(
            OfertaLojaOut(
                produto_id=oferta.id,
                loja=loja,
                url_produto=oferta.url_produto,
                preco_atual=_duas_casas(ultima.preco) if ultima else None,
                frete=_duas_casas(ultima.frete) if ultima else None,
                data_hora_coleta=ultima.data_hora_coleta if ultima else None,
                menor_preco=_duas_casas(min(c.preco for c in validas)) if validas else None,
            )
        )

    # Da mais barata para a mais cara; lojas ainda sem preço vão para o fim.
    ofertas.sort(key=lambda o: (o.preco_atual is None, o.preco_atual or Decimal(0)))
    com_preco = [o for o in ofertas if o.preco_atual is not None]
    melhor = com_preco[0].preco_atual if com_preco else None
    for o in com_preco:
        o.melhor_oferta = o.preco_atual == melhor

    return ComparativoLojasOut(
        produto_id=produto.id,
        nome=produto.nome,
        grupo_id=produto.grupo_id,
        ofertas=ofertas,
        melhor_oferta_produto_id=com_preco[0].produto_id if com_preco else None,
        economia=(com_preco[-1].preco_atual - melhor) if len(com_preco) >= 2 else None,
    )


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
    # Uma única consulta (JOIN) em vez de duas: o filtro por usuário vai junto (RNF01).
    produto = db.scalar(
        select(Produto)
        .join(Monitoramento, Monitoramento.produto_id == Produto.id)
        .where(Produto.id == produto_id, Monitoramento.usuario_id == usuario.id)
    )
    if produto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _MSG_NAO_ENCONTRADO)
    return produto


def _coletas_validas(db: Session, produto_id: uuid.UUID) -> list[Row]:
    """RN09: só coletas deste produto (nunca mistura com outro) e só válidas,
    da mais antiga para a mais recente.

    RNF01: usa o índice idx_historico_produto (produto_id, data_hora_coleta) e
    carrega só as colunas que o histórico e a análise usam, como linhas leves em
    vez de objetos ORM completos: com milhares de coletas, isso corta o tempo de
    resposta em mais da metade. As linhas expõem preco, data_hora_coleta e
    coleta_valida por atributo, que é o que AnaliseService e ColetaPrecoOut leem."""
    return list(
        db.execute(
            select(
                HistoricoPreco.preco,
                HistoricoPreco.data_hora_coleta,
                HistoricoPreco.coleta_valida,
                HistoricoPreco.frete,
            )
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
            frete_atual=None,
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
        frete_atual=_duas_casas(coletas[-1].frete),
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
    janela_dias: int | None = Query(
        default=None,
        ge=0,
        le=3650,
        description="Janela da média em dias (0 = todo o histórico). Omitido: usa ANALISE_JANELA_DIAS.",
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    produto = _produto_monitorado_pelo_usuario(db, produto_id, usuario)
    coletas = _coletas_validas(db, produto_id)
    minimo = _analise_service.min_amostras_media
    janela = _analise_service.janela_dias if janela_dias is None else janela_dias

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
            janela_dias=janela,
        )

    # RN10: sem amostras suficientes o serviço devolve SEM_DADOS (não classifica queda).
    r = _analise_service.classificar(coletas, janela_dias=janela)

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
        janela_dias=r.janela_dias,
    )
