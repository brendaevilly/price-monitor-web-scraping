from app.dependencies import get_usuario_atual
from app.main import app

URL = "https://www.kabum.com.br/produto/123/mouse-gamer"


def _loja(client):
    return client.post("/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}).json()


def _produto_existente(client):
    """Cadastra um produto (e um monitoramento inicial) só para ter um
    produto_id já existente no catálogo, como outro usuário faria."""
    loja = _loja(client)
    resp = client.post("/produtos", json={
        "nome": "Mouse Gamer", "url_produto": URL, "loja_id": loja["id"],
    })
    return resp.json()["produto_id"]


# ---------- POST /monitoramentos (UC04) ----------

def test_criar_monitoramento_ok(client, outro_usuario):
    produto_id = _produto_existente(client)

    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    r = client.post("/monitoramentos", json={"produto_id": produto_id, "preco_alvo": "199.90"})

    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["produto_id"] == produto_id
    assert float(corpo["preco_alvo"]) == 199.90
    assert corpo["alerta_ativo"] is True  # nasce ativo


def test_criar_monitoramento_sem_preco_alvo(client, outro_usuario):
    produto_id = _produto_existente(client)
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    r = client.post("/monitoramentos", json={"produto_id": produto_id})
    assert r.status_code == 201
    assert r.json()["preco_alvo"] is None


def test_criar_monitoramento_produto_inexistente(client):
    r = client.post(
        "/monitoramentos",
        json={"produto_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 422
    assert "Produto não encontrado" in r.json()["detail"]


def test_criar_monitoramento_duplicado(client):
    produto_id = _produto_existente(client)
    # O próprio usuário que criou o produto já está monitorando (via POST /produtos).
    r = client.post("/monitoramentos", json={"produto_id": produto_id})
    assert r.status_code == 409
    assert "já está monitorando" in r.json()["detail"]


def test_criar_monitoramento_preco_alvo_invalido(client, outro_usuario):
    produto_id = _produto_existente(client)
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    assert client.post(
        "/monitoramentos", json={"produto_id": produto_id, "preco_alvo": "0"}
    ).status_code == 422
    assert client.post(
        "/monitoramentos", json={"produto_id": produto_id, "preco_alvo": "-10"}
    ).status_code == 422


# ---------- PATCH /monitoramentos/{id} (UC08) ----------

def test_atualizar_desativar_alerta(client):
    produto_id = _produto_existente(client)
    monitoramento_id = client.get("/produtos").json()[0]["monitoramento_id"]

    r = client.patch(f"/monitoramentos/{monitoramento_id}", json={"alerta_ativo": False})
    assert r.status_code == 200, r.text
    assert r.json()["alerta_ativo"] is False


def test_atualizar_definir_preco_alvo(client):
    produto_id = _produto_existente(client)
    monitoramento_id = client.get("/produtos").json()[0]["monitoramento_id"]

    r = client.patch(f"/monitoramentos/{monitoramento_id}", json={"preco_alvo": "150.00"})
    assert r.status_code == 200
    assert float(r.json()["preco_alvo"]) == 150.00


def test_atualizar_remover_preco_alvo_com_null(client):
    produto_id = _produto_existente(client)
    monitoramento_id = client.get("/produtos").json()[0]["monitoramento_id"]
    client.patch(f"/monitoramentos/{monitoramento_id}", json={"preco_alvo": "150.00"})

    r = client.patch(f"/monitoramentos/{monitoramento_id}", json={"preco_alvo": None})
    assert r.status_code == 200
    assert r.json()["preco_alvo"] is None


def test_atualizar_sem_nenhum_campo_retorna_422(client):
    produto_id = _produto_existente(client)
    monitoramento_id = client.get("/produtos").json()[0]["monitoramento_id"]
    r = client.patch(f"/monitoramentos/{monitoramento_id}", json={})
    assert r.status_code == 422


def test_atualizar_monitoramento_inexistente(client):
    r = client.patch(
        "/monitoramentos/00000000-0000-0000-0000-000000000000",
        json={"alerta_ativo": False},
    )
    assert r.status_code == 404


def test_atualizar_monitoramento_de_outro_usuario_nao_e_permitido(client, outro_usuario):
    produto_id = _produto_existente(client)
    monitoramento_id = client.get("/produtos").json()[0]["monitoramento_id"]

    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    r = client.patch(f"/monitoramentos/{monitoramento_id}", json={"alerta_ativo": False})
    assert r.status_code == 404  # não revela que o recurso existe


def test_endpoints_exigem_autenticacao(db):
    from fastapi.testclient import TestClient
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    assert c.post("/monitoramentos", json={"produto_id": "00000000-0000-0000-0000-000000000000"}).status_code == 401
    assert c.patch("/monitoramentos/00000000-0000-0000-0000-000000000000", json={"alerta_ativo": True}).status_code == 401
    app.dependency_overrides.clear()
