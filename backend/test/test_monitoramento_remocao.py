import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.dependencies import get_usuario_atual
from app.main import app
from app.models.historico_preco import HistoricoPreco
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto

URL = "https://www.kabum.com.br/produto/123/mouse-gamer"


@pytest.fixture()
def cadastro(client):
    """Produto cadastrado pelo usuário padrão: devolve (produto_id, monitoramento_id)."""
    loja = client.post("/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}).json()
    r = client.post("/produtos", json={"nome": "Mouse Gamer", "url_produto": URL, "loja_id": loja["id"]})
    assert r.status_code == 201, r.text
    return r.json()["produto_id"], r.json()["monitoramento_id"]


def _coletas(db, produto_id, n=3):
    for i in range(n):
        db.add(HistoricoPreco(
            produto_id=uuid.UUID(produto_id),
            preco=Decimal("100"),
            data_hora_coleta=datetime(2026, 1, 1 + i, tzinfo=timezone.utc),
        ))
    db.commit()


def _produto(db, produto_id):
    db.expire_all()
    return db.get(Produto, uuid.UUID(produto_id))


def test_remover_some_da_lista_do_usuario(client, cadastro):
    _, monitoramento_id = cadastro
    assert len(client.get("/produtos").json()) == 1

    r = client.delete(f"/monitoramentos/{monitoramento_id}")

    assert r.status_code == 204
    assert r.content == b""
    assert client.get("/produtos").json() == []


def test_remover_preserva_historico_rn05(client, db, cadastro):
    produto_id, monitoramento_id = cadastro
    _coletas(db, produto_id, 3)

    client.delete(f"/monitoramentos/{monitoramento_id}")

    db.expire_all()
    restantes = db.query(HistoricoPreco).filter(HistoricoPreco.produto_id == uuid.UUID(produto_id)).count()
    assert restantes == 3
    assert _produto(db, produto_id) is not None


def test_remover_ultimo_monitoramento_para_a_coleta(client, db, cadastro):
    produto_id, monitoramento_id = cadastro
    assert _produto(db, produto_id).ativo is True

    client.delete(f"/monitoramentos/{monitoramento_id}")

    assert _produto(db, produto_id).ativo is False
    # É o filtro usado por ColetaService.executar_coleta_ativos (RF06).
    ativos = db.query(Produto).filter(Produto.ativo.is_(True)).all()
    assert ativos == []


def test_remover_mantem_coleta_se_outro_usuario_monitora(client, db, usuario, outro_usuario, cadastro):
    produto_id, monitoramento_id = cadastro
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    assert client.post("/monitoramentos", json={"produto_id": produto_id}).status_code == 201

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    assert client.delete(f"/monitoramentos/{monitoramento_id}").status_code == 204

    assert _produto(db, produto_id).ativo is True  # outro usuário ainda monitora
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    assert len(client.get("/produtos").json()) == 1


def test_remover_nao_afeta_monitoramento_de_outro_usuario(client, db, usuario, outro_usuario, cadastro):
    produto_id, _ = cadastro
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario
    monitoramento_do_outro = client.post("/monitoramentos", json={"produto_id": produto_id}).json()["monitoramento_id"]

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    client.delete(f"/monitoramentos/{cadastro[1]}")

    db.expire_all()
    assert db.get(Monitoramento, uuid.UUID(monitoramento_do_outro)) is not None


def test_remover_de_outro_usuario_404_e_nada_muda(client, db, outro_usuario, cadastro):
    produto_id, monitoramento_id = cadastro
    app.dependency_overrides[get_usuario_atual] = lambda: outro_usuario

    r = client.delete(f"/monitoramentos/{monitoramento_id}")

    assert r.status_code == 404  # RNF03: não revela que existe
    db.expire_all()
    assert db.get(Monitoramento, uuid.UUID(monitoramento_id)) is not None
    assert _produto(db, produto_id).ativo is True


def test_remover_inexistente_404(client):
    r = client.delete("/monitoramentos/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_remover_duas_vezes_404(client, cadastro):
    _, monitoramento_id = cadastro
    assert client.delete(f"/monitoramentos/{monitoramento_id}").status_code == 204
    assert client.delete(f"/monitoramentos/{monitoramento_id}").status_code == 404


def test_monitorar_de_novo_reativa_produto_e_recupera_historico(client, db, cadastro):
    produto_id, monitoramento_id = cadastro
    _coletas(db, produto_id, 2)
    client.delete(f"/monitoramentos/{monitoramento_id}")
    assert _produto(db, produto_id).ativo is False

    r = client.post("/monitoramentos", json={"produto_id": produto_id})

    assert r.status_code == 201
    assert _produto(db, produto_id).ativo is True
    historico = client.get(f"/produtos/{produto_id}/historico").json()
    assert len(historico["coletas"]) == 2  # o histórico antigo continua lá