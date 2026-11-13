"""Um produto monitorado em mais de uma loja (issue #104)."""

from decimal import Decimal

import pytest

from app.models.historico_preco import HistoricoPreco
from app.models.produto import Produto

URL_KABUM = "https://www.kabum.com.br/produto/123/mouse-gamer"
URL_MAGALU = "https://www.magazineluiza.com.br/mouse-gamer/p/abc/"
URL_AMAZON = "https://www.amazon.com.br/dp/B0001"


def _loja(client, nome, dominio):
    return client.post("/lojas", json={"nome": nome, "dominio": dominio}).json()["id"]


@pytest.fixture()
def lojas(client):
    return {
        "kabum": _loja(client, "Kabum", "kabum.com.br"),
        "magalu": _loja(client, "Magazine Luiza", "magazineluiza.com.br"),
        "amazon": _loja(client, "Amazon", "amazon.com.br"),
    }


def _produto(client, lojas, **extra):
    corpo = {"nome": "Mouse Gamer", "url_produto": URL_KABUM, "loja_id": lojas["kabum"], **extra}
    return client.post("/produtos", json=corpo)


def _coleta(db, produto_id, preco, frete=None, valida=True, minutos=0):
    import uuid
    from datetime import datetime, timedelta, timezone

    produto_id = uuid.UUID(str(produto_id))

    db.add(HistoricoPreco(
        produto_id=produto_id, preco=Decimal(preco),
        frete=None if frete is None else Decimal(frete), coleta_valida=valida,
        data_hora_coleta=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minutos),
    ))
    db.commit()


# ---------- cadastro ----------

def test_cadastrar_com_outras_lojas_cria_um_produto_por_loja(client, lojas):
    r = _produto(
        client, lojas, preco_alvo="300.00",
        outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}],
    )
    assert r.status_code == 201, r.text
    lista = client.get("/produtos").json()
    assert len(lista) == 2
    assert {p["loja"]["dominio"] for p in lista} == {"kabum.com.br", "magazineluiza.com.br"}
    assert len({p["grupo_id"] for p in lista}) == 1 and lista[0]["grupo_id"] is not None
    assert {p["nome"] for p in lista} == {"Mouse Gamer"}
    assert {p["preco_alvo"] for p in lista} == {"300.00"}  # herda o preço-alvo


def test_produto_sem_outras_lojas_continua_sem_grupo(client, lojas):
    r = _produto(client, lojas)
    assert r.status_code == 201 and r.json()["grupo_id"] is None


def test_outra_loja_com_url_de_loja_errada_rejeita_tudo(client, lojas):
    r = _produto(client, lojas, outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_AMAZON}])
    assert r.status_code == 422
    assert client.get("/produtos").json() == []  # nada foi salvo


def test_mesma_loja_duas_vezes_e_rejeitada(client, lojas):
    r = _produto(client, lojas, outras_lojas=[
        {"loja_id": lojas["kabum"], "url_produto": "https://www.kabum.com.br/produto/999/outro"},
    ])
    assert r.status_code == 422 and client.get("/produtos").json() == []


def test_limite_de_outras_lojas(client, lojas):
    extras = [{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}] * 6
    assert _produto(client, lojas, outras_lojas=extras).status_code == 422


def test_falha_em_uma_loja_nao_salva_as_outras(client, lojas):
    # o usuário já monitora a URL da Magalu isoladamente...
    assert client.post("/produtos", json={
        "nome": "Mouse", "url_produto": URL_MAGALU, "loja_id": lojas["magalu"]}).status_code == 201
    # ...e tenta cadastrar a Kabum + a mesma URL da Magalu como "outra loja": 409 e nada novo salvo
    r = _produto(client, lojas, outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}])
    assert r.status_code == 409
    assert [p["loja"]["dominio"] for p in client.get("/produtos").json()] == ["magazineluiza.com.br"]


# ---------- adicionar loja a um produto existente ----------

def test_adicionar_loja_a_produto_existente(client, lojas):
    origem = _produto(client, lojas, preco_alvo="250.00").json()
    r = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["magalu"], "url_produto": URL_MAGALU})
    assert r.status_code == 201, r.text
    nova = r.json()
    assert nova["loja"]["dominio"] == "magazineluiza.com.br"
    assert nova["nome"] == "Mouse Gamer" and nova["preco_alvo"] == "250.00"
    lista = {p["produto_id"]: p for p in client.get("/produtos").json()}
    assert lista[origem["produto_id"]]["grupo_id"] == nova["grupo_id"] is not None


def test_adicionar_terceira_loja_reaproveita_o_grupo(client, lojas):
    origem = _produto(client, lojas).json()
    a = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}).json()
    b = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["amazon"], "url_produto": URL_AMAZON,
                          "nome": "Mouse Gamer Amazon", "preco_alvo": "199.90"}).json()
    assert a["grupo_id"] == b["grupo_id"]
    assert b["nome"] == "Mouse Gamer Amazon" and b["preco_alvo"] == "199.90"


def test_adicionar_loja_repetida_retorna_409(client, lojas):
    origem = _produto(client, lojas).json()
    r = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["kabum"], "url_produto": "https://www.kabum.com.br/produto/9/x"})
    assert r.status_code == 409


def test_adicionar_loja_com_url_de_outra_loja_retorna_422(client, lojas):
    origem = _produto(client, lojas).json()
    r = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["magalu"], "url_produto": URL_AMAZON})
    assert r.status_code == 422


def test_adicionar_loja_a_produto_de_outro_usuario_retorna_404(client, lojas, db, outro_usuario):
    from app.models.monitoramento import Monitoramento

    origem = _produto(client, lojas).json()
    import uuid

    db.query(Monitoramento).delete()
    db.add(Monitoramento(usuario_id=outro_usuario.id, produto_id=uuid.UUID(origem["produto_id"])))
    db.commit()
    r = client.post(f"/produtos/{origem['produto_id']}/lojas",
                    json={"loja_id": lojas["magalu"], "url_produto": URL_MAGALU})
    assert r.status_code == 404


def test_url_que_o_usuario_ja_monitora_retorna_409(client, lojas):
    _produto(client, lojas, outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}])
    b = client.post("/produtos", json={
        "nome": "Teclado", "url_produto": "https://www.kabum.com.br/produto/777/teclado",
        "loja_id": lojas["kabum"]}).json()
    # a URL da Magalu já é monitorada (no grupo do mouse): não pode ser reaproveitada aqui
    r = client.post(f"/produtos/{b['produto_id']}/lojas",
                    json={"loja_id": lojas["magalu"], "url_produto": URL_MAGALU})
    assert r.status_code == 409


# ---------- comparativo ----------

def test_comparativo_ordena_pela_oferta_mais_barata(client, lojas, db):
    origem = _produto(client, lojas, outras_lojas=[
        {"loja_id": lojas["magalu"], "url_produto": URL_MAGALU},
        {"loja_id": lojas["amazon"], "url_produto": URL_AMAZON},
    ]).json()
    por_dominio = {p["loja"]["dominio"]: p["produto_id"] for p in client.get("/produtos").json()}

    _coleta(db, por_dominio["kabum.com.br"], "120.00", frete="20.00", minutos=1)
    _coleta(db, por_dominio["kabum.com.br"], "150.00", frete="20.00", minutos=2)  # preço atual
    _coleta(db, por_dominio["magazineluiza.com.br"], "130.00", frete="0.00")
    # Amazon: só coleta inválida -> sem preço (RN09)
    _coleta(db, por_dominio["amazon.com.br"], "1.00", valida=False)

    r = client.get(f"/produtos/{origem['produto_id']}/lojas")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert [o["loja"]["dominio"] for o in corpo["ofertas"]] == [
        "magazineluiza.com.br", "kabum.com.br", "amazon.com.br"
    ]
    magalu, kabum, amazon = corpo["ofertas"]
    assert (magalu["preco_atual"], magalu["frete"], magalu["melhor_oferta"]) == ("130.00", "0.00", True)
    assert (kabum["preco_atual"], kabum["menor_preco"], kabum["melhor_oferta"]) == ("150.00", "120.00", False)
    assert amazon["preco_atual"] is None and amazon["melhor_oferta"] is False
    assert corpo["melhor_oferta_produto_id"] == por_dominio["magazineluiza.com.br"]
    assert corpo["economia"] == "20.00"


def test_comparativo_de_produto_de_uma_loja_so(client, lojas, db):
    origem = _produto(client, lojas).json()
    _coleta(db, origem["produto_id"], "99.90")
    corpo = client.get(f"/produtos/{origem['produto_id']}/lojas").json()
    assert corpo["grupo_id"] is None and len(corpo["ofertas"]) == 1
    assert corpo["ofertas"][0]["melhor_oferta"] is True and corpo["economia"] is None


def test_comparativo_sem_coletas(client, lojas):
    origem = _produto(client, lojas).json()
    corpo = client.get(f"/produtos/{origem['produto_id']}/lojas").json()
    assert corpo["melhor_oferta_produto_id"] is None and corpo["ofertas"][0]["preco_atual"] is None


def test_comparativo_so_lista_lojas_do_usuario(client, lojas, db, outro_usuario):
    from app.models.monitoramento import Monitoramento

    origem = _produto(client, lojas, outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}]).json()
    magalu = next(p for p in client.get("/produtos").json() if p["loja"]["dominio"] == "magazineluiza.com.br")
    # o usuário deixa de monitorar a Magalu: ela some do comparativo dele
    assert client.delete(f"/monitoramentos/{magalu['monitoramento_id']}").status_code == 204
    corpo = client.get(f"/produtos/{origem['produto_id']}/lojas").json()
    assert [o["loja"]["dominio"] for o in corpo["ofertas"]] == ["kabum.com.br"]


def test_comparativo_de_produto_inexistente_retorna_404(client):
    assert client.get("/produtos/00000000-0000-0000-0000-000000000000/lojas").status_code == 404


# ---------- o robô coleta todas as lojas ----------

def test_robo_coleta_todas_as_ofertas_do_grupo(client, lojas, db):
    from app.services.coleta_service import ColetaService

    _produto(client, lojas, outras_lojas=[{"loja_id": lojas["magalu"], "url_produto": URL_MAGALU}])
    vistos = []

    class Falso(ColetaService):
        def executar_coleta(self, produto, db=None):
            vistos.append(produto.url_produto)
            return None

    Falso().executar_coleta_ativos(db)
    assert sorted(vistos) == sorted([URL_KABUM, URL_MAGALU])
