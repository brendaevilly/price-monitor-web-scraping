from app.dependencies import get_usuario_atual
from app.main import app

URL = "https://www.kabum.com.br/produto/123/mouse-gamer"


def _loja(client, nome="KaBuM!", dominio="kabum.com.br"):
    return client.post("/lojas", json={"nome": nome, "dominio": dominio})


def _produto(client, loja_id, **extra):
    corpo = {"nome": "Mouse Gamer", "url_produto": URL, "loja_id": loja_id, **extra}
    return client.post("/produtos", json=corpo)


# ---------- Loja ----------
def test_cadastrar_loja_normaliza_dominio(client):
    r = _loja(client, dominio="https://WWW.KaBum.com.br/promo")
    assert r.status_code == 201
    assert r.json()["dominio"] == "kabum.com.br"


def test_loja_duplicada_retorna_409(client):
    _loja(client)
    assert _loja(client, nome="Outra", dominio="www.kabum.com.br").status_code == 409


def test_loja_dominio_invalido_retorna_422(client):
    assert _loja(client, dominio="127.0.0.1").status_code == 422
    assert _loja(client, dominio="semponto").status_code == 422
    assert client.post("/lojas", json={"nome": "X", "dominio": "a.com"}).status_code == 422


def test_listar_lojas(client):
    _loja(client)
    _loja(client, nome="Amazon", dominio="amazon.com.br")
    assert [l["nome"] for l in client.get("/lojas").json()] == ["Amazon", "KaBuM!"]


# ---------- Produto ----------
def test_cadastrar_produto_ok(client):
    loja_id = _loja(client).json()["id"]
    r = _produto(client, loja_id, preco_alvo="199.90")
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["url_produto"] == URL
    assert corpo["loja"]["dominio"] == "kabum.com.br"
    assert float(corpo["preco_alvo"]) == 199.90
    assert corpo["alerta_ativo"] is True and corpo["ativo"] is True
    assert len(client.get("/produtos").json()) == 1


def test_produto_sem_preco_alvo(client):
    loja_id = _loja(client).json()["id"]
    r = _produto(client, loja_id)
    assert r.status_code == 201 and r.json()["preco_alvo"] is None


def test_produto_loja_inexistente(client):
    r = _produto(client, "00000000-0000-0000-0000-000000000000")
    assert r.status_code == 422 and "Loja não encontrada" in r.json()["detail"]


def test_produto_url_de_outra_loja_rejeitada(client):
    loja_id = _loja(client, "Amazon", "amazon.com.br").json()["id"]
    r = _produto(client, loja_id)  # URL é da KaBuM
    assert r.status_code == 422 and "não pertence" in r.json()["detail"]
    assert client.get("/produtos").json() == []  # nada foi salvo


def test_produto_url_invalida_rejeitada(client):
    loja_id = _loja(client).json()["id"]
    for url in ["nao-e-url", "https://www.kabum.com.br/", "http://localhost/p/1"]:
        r = client.post("/produtos", json={"nome": "X1", "url_produto": url, "loja_id": loja_id})
        assert r.status_code == 422, url


def test_produto_campos_obrigatorios_e_preco_invalido(client):
    loja_id = _loja(client).json()["id"]
    assert client.post("/produtos", json={"loja_id": loja_id}).status_code == 422
    assert _produto(client, loja_id, preco_alvo="0").status_code == 422
    assert _produto(client, loja_id, preco_alvo="-5").status_code == 422


def test_mesmo_usuario_nao_duplica_monitoramento(client):
    loja_id = _loja(client).json()["id"]
    _produto(client, loja_id)
    assert _produto(client, loja_id).status_code == 409


def test_produto_e_compartilhado_entre_usuarios(client, outro_usuario):
    loja_id = _loja(client).json()["id"]
    p1 = _produto(client, loja_id).json()
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    p2 = _produto(client, loja_id, preco_alvo="150").json()
    assert p1["produto_id"] == p2["produto_id"]            # mesmo Produto (mesmo histórico)
    assert p1["monitoramento_id"] != p2["monitoramento_id"]  # monitoramentos individuais
    assert len(client.get("/produtos").json()) == 1          # só vê o próprio


def test_endpoints_exigem_autenticacao(db):
    from fastapi.testclient import TestClient
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    assert c.get("/produtos").status_code == 401
    assert c.post("/lojas", json={"nome": "X", "dominio": "x.com"}).status_code == 401
    app.dependency_overrides.clear()
