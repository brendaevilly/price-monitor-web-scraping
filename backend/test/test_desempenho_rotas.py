"""Base de desempenho (RNF01): rotas principais em até 2 s, sem contar scraping.

Roda no SQLite em memória, então mede o código da API e o uso do índice, não a
latência do Supabase/rede. A medição em ambiente real é feita com
scripts/medir_tempo_resposta.py e registrada em docs/desempenho.md.
O login usa o Supabase Auth por fora do nosso código: aqui ele é simulado.
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import insert, text

from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.routers import usuario as usuario_router

META_SEGUNDOS = 2.0
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _medir(chamada, repeticoes=5):
    chamada()  # aquecimento
    piores = 0.0
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resposta = chamada()
        piores = max(piores, time.perf_counter() - inicio)
        assert resposta.status_code == 200, resposta.text
    return piores


def _popular(db, usuario, coletas_alvo=3000, outros_produtos=40, coletas_outros=100):
    loja = Loja(nome="KaBuM!", dominio="kabum.com.br")
    db.add(loja)
    db.flush()
    ids = []
    for i in range(outros_produtos + 1):
        p = Produto(nome=f"P{i}", url_produto=f"https://www.kabum.com.br/p/{i}", loja_id=loja.id)
        db.add(p)
        db.flush()
        db.add(Monitoramento(usuario_id=usuario.id, produto_id=p.id))
        ids.append(p.id)
    alvo, outros = ids[0], ids[1:]
    linhas = [
        dict(id=uuid.uuid4(), produto_id=alvo, preco=Decimal("100") - Decimal(i % 7),
             data_hora_coleta=BASE + timedelta(minutes=i), coleta_valida=True)
        for i in range(coletas_alvo)
    ]
    for pid in outros:
        linhas += [
            dict(id=uuid.uuid4(), produto_id=pid, preco=Decimal("50"),
                 data_hora_coleta=BASE + timedelta(minutes=i), coleta_valida=True)
            for i in range(coletas_outros)
        ]
    db.execute(insert(HistoricoPreco), linhas)
    db.commit()
    return alvo


def test_indice_historico_por_produto_e_data_hora():
    indices = {i.name: [c.name for c in i.columns] for i in HistoricoPreco.__table__.indexes}
    assert indices.get("idx_historico_produto") == ["produto_id", "data_hora_coleta"]


def test_consulta_do_historico_usa_o_indice(db, usuario):
    alvo = _popular(db, usuario, coletas_alvo=200)
    plano = db.execute(
        text(
            "EXPLAIN QUERY PLAN SELECT * FROM historico_precos "
            "WHERE produto_id = :p AND coleta_valida = 1 ORDER BY data_hora_coleta"
        ),
        {"p": alvo.hex},
    ).fetchall()
    detalhe = " ".join(str(linha[-1]) for linha in plano)
    assert "idx_historico_produto" in detalhe, detalhe
    assert "TEMP B-TREE" not in detalhe  # o índice já entrega ordenado, sem sort extra


def test_rotas_principais_dentro_da_meta(client, db, usuario, monkeypatch):
    alvo = _popular(db, usuario)

    monkeypatch.setattr(
        usuario_router,
        "_entrar",
        lambda email, senha: SimpleNamespace(
            session=SimpleNamespace(access_token="a", refresh_token="r", expires_in=3600),
            user=SimpleNamespace(id=usuario.id),
        ),
    )

    tempos = {
        "login": _medir(lambda: client.post("/usuarios/login", json={"email": "ana@exemplo.com", "senha": "senha1234"})),
        "produtos": _medir(lambda: client.get("/produtos")),
        "historico": _medir(lambda: client.get(f"/produtos/{alvo}/historico")),
        "analise": _medir(lambda: client.get(f"/produtos/{alvo}/analise")),
    }
    for rota, segundos in tempos.items():
        assert segundos <= META_SEGUNDOS, f"{rota}: {segundos:.3f}s > {META_SEGUNDOS}s ({tempos})"
