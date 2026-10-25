import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.dependencies import get_usuario_atual
from app.main import app
from app.models.alerta import Alerta

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _produto(client, slug="mouse"):
    loja = client.get("/lojas").json()
    loja_id = loja[0]["id"] if loja else client.post(
        "/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}
    ).json()["id"]
    r = client.post("/produtos", json={
        "nome": f"Produto {slug}",
        "url_produto": f"https://www.kabum.com.br/produto/{slug}",
        "loja_id": loja_id,
    })
    assert r.status_code == 201, r.text
    return r.json()["produto_id"]


def _alerta(db, usuario, produto_id, tipo="queda_preco", dias=0, mensagem="msg"):
    a = Alerta(
        produto_id=uuid.UUID(produto_id),
        usuario_id=usuario.id,
        tipo=tipo,
        mensagem=mensagem,
        data_envio=BASE + timedelta(days=dias),
    )
    db.add(a)
    db.commit()
    return a


@pytest.fixture()
def produto_id(client):
    return _produto(client)


def test_listar_sem_alertas(client):
    r = client.get("/alertas")
    assert r.status_code == 200
    assert r.json() == []


def test_listar_devolve_produto_tipo_data_e_mensagem(client, db, usuario, produto_id):
    _alerta(db, usuario, produto_id, tipo="preco_alvo", mensagem="Preço-alvo atingido")

    corpo = client.get("/alertas").json()

    assert len(corpo) == 1
    alerta = corpo[0]
    assert alerta["tipo"] == "preco_alvo"
    assert alerta["mensagem"] == "Preço-alvo atingido"
    assert alerta["data_envio"].startswith("2026-01-01")
    assert alerta["produto"] == {
        "id": produto_id,
        "nome": "Produto mouse",
        "url_produto": "https://www.kabum.com.br/produto/mouse",
    }


def test_listar_mais_recentes_primeiro(client, db, usuario, produto_id):
    _alerta(db, usuario, produto_id, dias=0, mensagem="antigo")
    _alerta(db, usuario, produto_id, dias=2, mensagem="novo")
    _alerta(db, usuario, produto_id, dias=1, mensagem="meio")

    mensagens = [a["mensagem"] for a in client.get("/alertas").json()]
    assert mensagens == ["novo", "meio", "antigo"]


def test_listar_so_do_dono_rnf03(client, db, usuario, outro_usuario, produto_id):
    _alerta(db, usuario, produto_id, mensagem="meu")
    _alerta(db, outro_usuario, produto_id, mensagem="do outro")

    mensagens = [a["mensagem"] for a in client.get("/alertas").json()]
    assert mensagens == ["meu"]

    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    mensagens = [a["mensagem"] for a in client.get("/alertas").json()]
    assert mensagens == ["do outro"]


def test_listar_respeita_limite(client, db, usuario, produto_id):
    for i in range(5):
        _alerta(db, usuario, produto_id, dias=i, mensagem=f"m{i}")

    corpo = client.get("/alertas", params={"limite": 2}).json()
    assert [a["mensagem"] for a in corpo] == ["m4", "m3"]


@pytest.mark.parametrize("limite", [0, -1, 201])
def test_listar_limite_invalido(client, limite):
    assert client.get("/alertas", params={"limite": limite}).status_code == 422


def test_listar_exige_autenticacao(client):
    app.dependency_overrides.pop(get_usuario_atual)
    r = client.get("/alertas")
    assert r.status_code == 401