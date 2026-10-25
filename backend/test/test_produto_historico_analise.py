import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.dependencies import get_usuario_atual
from app.main import app
from app.models.historico_preco import HistoricoPreco

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _loja(client):
    return client.post("/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}).json()


def _produto(client, loja_id, slug="mouse"):
    r = client.post("/produtos", json={
        "nome": f"Produto {slug}",
        "url_produto": f"https://www.kabum.com.br/produto/{slug}",
        "loja_id": loja_id,
    })
    assert r.status_code == 201, r.text
    return r.json()["produto_id"]


def _coletas(db, produto_id, precos, valida=True, inicio=0):
    """Insere uma coleta por preço, um dia após a outra."""
    for i, preco in enumerate(precos, start=inicio):
        db.add(HistoricoPreco(
            produto_id=uuid.UUID(produto_id),
            preco=Decimal(str(preco)),
            data_hora_coleta=BASE + timedelta(days=i),
            coleta_valida=valida,
        ))
    db.commit()


@pytest.fixture()
def produto_id(client):
    return _produto(client, _loja(client)["id"])


# ---------- GET /produtos/{id}/historico ----------

def test_historico_sem_coletas(client, produto_id):
    r = client.get(f"/produtos/{produto_id}/historico")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["coletas"] == []
    assert corpo["preco_atual"] is None
    assert corpo["menor_preco"] is None
    assert corpo["media_historica"] is None


def test_historico_ordem_cronologica_atual_e_menor(client, db, produto_id):
    # Inseridas fora de ordem de propósito.
    db.add_all([
        HistoricoPreco(produto_id=uuid.UUID(produto_id), preco=Decimal("120"), data_hora_coleta=BASE + timedelta(days=2)),
        HistoricoPreco(produto_id=uuid.UUID(produto_id), preco=Decimal("100"), data_hora_coleta=BASE),
        HistoricoPreco(produto_id=uuid.UUID(produto_id), preco=Decimal("80"), data_hora_coleta=BASE + timedelta(days=1)),
    ])
    db.commit()

    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert [float(c["preco"]) for c in corpo["coletas"]] == [100, 80, 120]
    assert float(corpo["preco_atual"]) == 120
    assert float(corpo["menor_preco"]) == 80


def test_historico_ignora_coletas_invalidas(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 100, 90])
    _coletas(db, produto_id, [1, 5000], valida=False, inicio=10)  # RN09

    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert len(corpo["coletas"]) == 4
    assert float(corpo["preco_atual"]) == 90  # a inválida mais recente não vira preço atual
    assert float(corpo["menor_preco"]) == 90  # nem o menor


def test_historico_nao_mistura_produtos(client, db, produto_id):
    outro = _produto(client, _loja_existente(client), slug="teclado")
    _coletas(db, produto_id, [100, 110])
    _coletas(db, outro, [1, 2, 3])

    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert [float(c["preco"]) for c in corpo["coletas"]] == [100, 110]


def _loja_existente(client):
    return client.get("/lojas").json()[0]["id"]


def test_historico_media_so_com_amostras_suficientes(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 90])  # 2 anteriores: insuficiente (RN10)
    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert corpo["media_historica"] is None
    assert corpo["amostras_media"] == 2

    _coletas(db, produto_id, [100, 80], inicio=3)  # agora: 100,100,90,100 anteriores
    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert float(corpo["media_historica"]) == 97.5
    assert corpo["amostras_media"] == 4


def test_historico_media_arredondada_em_duas_casas(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 101, 50])  # média 100.3333...
    corpo = client.get(f"/produtos/{produto_id}/historico").json()
    assert float(corpo["media_historica"]) == 100.33


def test_historico_produto_inexistente(client):
    r = client.get("/produtos/00000000-0000-0000-0000-000000000000/historico")
    assert r.status_code == 404


def test_historico_produto_de_outro_usuario_404(client, outro_usuario, produto_id):
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    r = client.get(f"/produtos/{produto_id}/historico")
    assert r.status_code == 404  # RNF03: não revela que o produto existe


# ---------- GET /produtos/{id}/analise (UC11) ----------

def _analise(client, produto_id):
    r = client.get(f"/produtos/{produto_id}/analise")
    assert r.status_code == 200, r.text
    return r.json()


def test_analise_sem_coletas(client, produto_id):
    corpo = _analise(client, produto_id)
    assert corpo["classificacao"] == "sem_dados"
    assert corpo["preco_atual"] is None
    assert corpo["queda_relevante"] is False


def test_analise_sem_amostras_suficientes_nao_classifica(client, db, produto_id):
    _coletas(db, produto_id, [100, 50])  # queda enorme, mas só 1 anterior (RN10)
    corpo = _analise(client, produto_id)
    assert corpo["classificacao"] == "sem_dados"
    assert corpo["media_historica"] is None
    assert corpo["variacao_percentual_media"] is None
    assert corpo["queda_relevante"] is False
    assert corpo["amostras_media"] == 1
    assert corpo["amostras_minimas"] == 3
    # A variação contra a coleta anterior continua sendo informada (UC11, 3a).
    assert corpo["variacao_percentual_anterior"] == 50.0


@pytest.mark.parametrize("atual, classificacao, variacao", [
    (110, "sem_queda", -10.0),      # subiu
    (100, "sem_queda", 0.0),        # igual
    (96, "sem_queda", 4.0),         # < 5% (UC11, 4a)
    (95, "pequena_queda", 5.0),     # limite inferior
    (91, "pequena_queda", 9.0),
    (90, "queda_relevante", 10.0),  # limite inferior
    (81, "queda_relevante", 19.0),
    (80, "grande_queda", 20.0),     # limite inferior
    (50, "grande_queda", 50.0),
])
def test_analise_faixas_do_uc11(client, db, produto_id, atual, classificacao, variacao):
    _coletas(db, produto_id, [100, 100, 100, atual])  # média de referência = 100
    corpo = _analise(client, produto_id)
    assert corpo["classificacao"] == classificacao
    assert corpo["variacao_percentual_media"] == variacao
    assert float(corpo["media_historica"]) == 100
    assert float(corpo["preco_atual"]) == atual
    assert corpo["queda_relevante"] is (classificacao in ("queda_relevante", "grande_queda"))


def test_analise_variacao_contra_coleta_anterior(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 200, 150])  # anterior 200 -> atual 150 = 25%
    corpo = _analise(client, produto_id)
    assert corpo["variacao_percentual_anterior"] == 25.0


def test_analise_ignora_coletas_invalidas(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 100, 90])
    _coletas(db, produto_id, [1], valida=False, inicio=10)  # falha de coleta (UC12/RN09)
    corpo = _analise(client, produto_id)
    assert float(corpo["preco_atual"]) == 90
    assert corpo["classificacao"] == "queda_relevante"


def test_analise_nao_mistura_produtos(client, db, produto_id):
    outro = _produto(client, _loja_existente(client), slug="teclado")
    _coletas(db, produto_id, [100, 100, 100, 100])
    _coletas(db, outro, [10, 10, 10, 1])

    corpo = _analise(client, produto_id)
    assert corpo["classificacao"] == "sem_queda"
    assert float(corpo["media_historica"]) == 100


def test_analise_produto_inexistente(client):
    r = client.get("/produtos/00000000-0000-0000-0000-000000000000/analise")
    assert r.status_code == 404


def test_analise_produto_de_outro_usuario_404(client, outro_usuario, produto_id):
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    assert client.get(f"/produtos/{produto_id}/analise").status_code == 404
