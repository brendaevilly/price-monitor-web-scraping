import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.dependencies import get_usuario_atual
from app.main import app
from app.models.historico_preco import HistoricoPreco

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _loja(client):
    lojas = client.get("/lojas").json()
    if lojas:
        return lojas[0]["id"]
    return client.post("/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}).json()["id"]


def _produto(client, slug):
    r = client.post("/produtos", json={
        "nome": f"Produto {slug}",
        "url_produto": f"https://www.kabum.com.br/produto/{slug}",
        "loja_id": _loja(client),
    })
    assert r.status_code == 201, r.text
    return r.json()["produto_id"]


def _coletas(db, produto_id, precos, dias=None, valida=True):
    dias = dias if dias is not None else range(len(precos))
    for p, d in zip(precos, dias):
        db.add(HistoricoPreco(
            produto_id=uuid.UUID(produto_id),
            preco=Decimal(str(p)) if valida else None,
            data_hora_coleta=BASE + timedelta(days=d),
            coleta_valida=valida,
        ))
    db.commit()


@pytest.fixture()
def produto_id(client):
    return _produto(client, "mouse")


# ---------- GET /produtos/{id}/analise?janela_dias= ----------

def test_analise_devolve_variacoes_classificacao_e_janela_padrao(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 100, 90])
    corpo = client.get(f"/produtos/{produto_id}/analise").json()
    assert corpo["variacao_percentual_anterior"] == 10.0
    assert corpo["variacao_percentual_media"] == 10.0
    assert corpo["classificacao"] == "queda_relevante"
    assert corpo["janela_dias"] == 30  # padrão da config


def test_analise_janela_dias_restringe_a_media(client, db, produto_id):
    # Coleta de 200 fica a 60 dias da última: dentro só com janela maior.
    _coletas(db, produto_id, [200, 100, 100, 100, 90], dias=[0, 60, 70, 80, 85])
    curta = client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": 30}).json()
    assert curta["amostras_media"] == 3 and curta["media_historica"] == "100.00"
    assert curta["janela_dias"] == 30
    tudo = client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": 0}).json()
    assert tudo["amostras_media"] == 4 and tudo["media_historica"] == "125.00"
    assert tudo["janela_dias"] == 0


def test_analise_janela_curta_demais_da_sem_dados(client, db, produto_id):
    _coletas(db, produto_id, [100, 100, 100, 90], dias=[0, 1, 2, 40])
    corpo = client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": 7}).json()
    assert corpo["classificacao"] == "sem_dados"
    assert corpo["media_historica"] is None
    assert corpo["variacao_percentual_media"] is None
    assert corpo["queda_relevante"] is False


@pytest.mark.parametrize("valor", [-1, 3651, "abc"])
def test_analise_janela_invalida_422(client, produto_id, valor):
    assert client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": valor}).status_code == 422


def test_analise_sem_coletas_informa_janela(client, produto_id):
    corpo = client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": 15}).json()
    assert corpo["classificacao"] == "sem_dados" and corpo["janela_dias"] == 15


# ---------- GET /analise/resumo ----------

def test_resumo_sem_produtos(client):
    r = client.get("/analise/resumo")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["produtos"] == [] and corpo["total_produtos"] == 0
    assert sum(corpo["contagem_por_classificacao"].values()) == 0


def test_resumo_traz_todos_os_produtos_com_dados(client, db):
    a = _produto(client, "a")
    b = _produto(client, "b")
    c = _produto(client, "c")
    _coletas(db, a, [100, 100, 100, 90])        # relevante
    _coletas(db, b, [100, 100, 100, 70, 80])    # preço atual 80, menor 70
    # c sem coletas

    corpo = client.get("/analise/resumo").json()
    por_id = {p["produto_id"]: p for p in corpo["produtos"]}

    assert corpo["total_produtos"] == 3
    assert corpo["amostras_minimas"] == 3
    assert corpo["janela_dias"] == 30

    assert por_id[a]["classificacao"] == "queda_relevante"
    assert por_id[a]["preco_atual"] == "90.00" and por_id[a]["menor_preco"] == "90.00"
    assert por_id[a]["variacao_percentual_media"] == 10.0
    assert por_id[a]["variacao_percentual_anterior"] == 10.0

    # média das 4 anteriores = 92.50; 80 => 13.51% de queda; menor preço histórico = 70
    assert por_id[b]["preco_atual"] == "80.00" and por_id[b]["menor_preco"] == "70.00"
    assert por_id[b]["media_historica"] == "92.50"
    assert por_id[b]["variacao_percentual_media"] == 13.51
    assert por_id[b]["classificacao"] == "queda_relevante"

    assert por_id[c]["classificacao"] == "sem_dados"
    assert por_id[c]["preco_atual"] is None and por_id[c]["menor_preco"] is None
    assert por_id[c]["queda_relevante"] is False

    assert corpo["contagem_por_classificacao"]["queda_relevante"] == 2
    assert corpo["contagem_por_classificacao"]["sem_dados"] == 1
    assert sum(corpo["contagem_por_classificacao"].values()) == 3


def test_resumo_sem_dados_suficientes_nao_classifica_queda(client, db):
    p = _produto(client, "poucos")
    _coletas(db, p, [100, 50])  # queda de 50%, mas só 1 coleta anterior
    item = client.get("/analise/resumo").json()["produtos"][0]
    assert item["classificacao"] == "sem_dados"
    assert item["variacao_percentual_media"] is None
    assert item["queda_relevante"] is False
    assert item["preco_atual"] == "50.00"


def test_resumo_ignora_coletas_invalidas(client, db):
    p = _produto(client, "inv")
    _coletas(db, p, [100, 100, 100, 100])
    _coletas(db, p, [None], dias=[10], valida=False)  # falha de scraping, mais recente
    item = client.get("/analise/resumo").json()["produtos"][0]
    assert item["preco_atual"] == "100.00"  # a inválida não vira "preço atual"
    assert item["classificacao"] == "sem_queda"


def test_resumo_nao_mistura_produtos(client, db):
    a = _produto(client, "a")
    b = _produto(client, "b")
    _coletas(db, a, [100, 100, 100, 100])
    _coletas(db, b, [10, 10, 10, 9])
    por_id = {p["produto_id"]: p for p in client.get("/analise/resumo").json()["produtos"]}
    assert por_id[a]["media_historica"] == "100.00" and por_id[a]["classificacao"] == "sem_queda"
    assert por_id[b]["media_historica"] == "10.00" and por_id[b]["classificacao"] == "queda_relevante"


def test_resumo_janela_dias(client, db):
    p = _produto(client, "j")
    _coletas(db, p, [200, 100, 100, 100, 90], dias=[0, 60, 70, 80, 85])
    padrao = client.get("/analise/resumo").json()["produtos"][0]
    todo = client.get("/analise/resumo", params={"janela_dias": 0}).json()
    assert padrao["media_historica"] == "100.00"
    assert todo["janela_dias"] == 0 and todo["produtos"][0]["media_historica"] == "125.00"


@pytest.mark.parametrize("valor", [-1, 3651])
def test_resumo_janela_invalida_422(client, valor):
    assert client.get("/analise/resumo", params={"janela_dias": valor}).status_code == 422


def test_resumo_so_do_dono_rnf03(client, db, usuario, outro_usuario):
    meu = _produto(client, "meu")
    _coletas(db, meu, [100, 100, 100, 90])

    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    assert client.get("/analise/resumo").json()["produtos"] == []
    outro = _produto(client, "dele")
    ids = [p["produto_id"] for p in client.get("/analise/resumo").json()["produtos"]]
    assert ids == [outro]

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    ids = [p["produto_id"] for p in client.get("/analise/resumo").json()["produtos"]]
    assert ids == [meu]


def test_analise_de_produto_de_outro_usuario_404(client, db, outro_usuario, produto_id):
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    r = client.get(f"/produtos/{produto_id}/analise", params={"janela_dias": 10})
    assert r.status_code == 404


def test_resumo_exige_autenticacao(client):
    app.dependency_overrides.pop(get_usuario_atual)
    assert client.get("/analise/resumo").status_code == 401
