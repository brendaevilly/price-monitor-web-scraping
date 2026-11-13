"""Frete na medição de preços (issue #105)."""

import json
from decimal import Decimal

import pytest

from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.seed_lojas import semear_lojas
from app.services.alerta_service import Analise, AlertaService
from app.services.coleta_service import (
    ColetaService,
    extrair_frete,
    interpretar_texto_frete,
)


def _ld(**oferta):
    dados = {"@type": "Product", "offers": {"@type": "Offer", "price": "100.00", **oferta}}
    return f'<html><script type="application/ld+json">{json.dumps(dados)}</script></html>'


# ---------- interpretar_texto_frete ----------

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Frete grátis", Decimal("0.00")),
        ("Chegará grátis amanhã", Decimal("0.00")),
        ("Entrega grátis para todo o Brasil", Decimal("0.00")),
        ("Frete: R$ 19,90", Decimal("19.90")),
        ("Entrega R$ 1.234,50 em 3 dias", Decimal("1234.50")),
        ("R$ 21,00 de frete", Decimal("21.00")),
        ("Frete grátis acima de R$ 99,00", None),  # condicional: não vale
        ("Frete grátis a partir de R$ 199", None),
        ("Frete grátis para compras acima de R$ 50", None),
        ("Avaliações dos clientes", None),
        ("", None),
    ],
)
def test_interpretar_texto_frete(texto, esperado):
    assert interpretar_texto_frete(texto) == esperado


# ---------- extrair_frete ----------

def test_frete_no_json_ld():
    html = _ld(shippingDetails={"shippingRate": {"@type": "MonetaryAmount", "value": "15.50"}})
    assert extrair_frete(html) == Decimal("15.50")


def test_frete_zero_no_json_ld_e_gratis():
    html = _ld(shippingDetails={"shippingRate": {"value": 0, "currency": "BRL"}})
    assert extrair_frete(html) == Decimal("0.00")


def test_frete_no_bloco_de_entrega():
    html = '<html><div class="ui-pdp-shipping"><p>Frete: R$ 12,30</p></div></html>'
    assert extrair_frete(html) == Decimal("12.30")


def test_frete_gratis_no_bloco_de_entrega():
    html = '<html><div data-testid="delivery-info">Frete grátis</div></html>'
    assert extrair_frete(html) == Decimal("0.00")


def test_banner_do_cabecalho_nao_conta_como_frete():
    html = (
        '<html><header><div class="shipping-banner">Frete grátis</div></header>'
        "<body><p>Produto</p></body></html>"
    )
    assert extrair_frete(html) is None


def test_pagina_sem_frete_devolve_none():
    assert extrair_frete("<html><body><h1>Mouse</h1></body></html>") is None


def test_bloco_gigante_e_ignorado():
    html = '<html><div class="entrega">' + ("texto " * 200) + " frete grátis</div></html>"
    assert extrair_frete(html) is None


# ---------- coleta: o frete entra na medição ----------

class _Resposta:
    def __init__(self, texto):
        self.text = texto
        self.status_code = 200

    def raise_for_status(self):
        pass


@pytest.fixture()
def produto(db, monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_INTERVALO_MINIMO_SEGUNDOS", 0)
    semear_lojas(db)
    loja = db.query(Loja).filter(Loja.dominio == "kabum.com.br").one()
    p = Produto(nome="Mouse", url_produto="https://www.kabum.com.br/produto/1/mouse", loja_id=loja.id)
    db.add(p)
    db.commit()
    return p


def _coletar(db, produto, monkeypatch, html):
    servico = ColetaService()
    monkeypatch.setattr(servico, "_requisitar", lambda url: _Resposta(html))
    return servico.executar_coleta(produto, db)


def test_coleta_soma_o_frete_ao_preco(db, produto, monkeypatch):
    html = _ld(shippingDetails={"shippingRate": {"value": "20.00"}})
    r = _coletar(db, produto, monkeypatch, html)
    assert r.coleta_valida
    assert (r.preco_produto, r.frete, r.preco) == (Decimal("100.00"), Decimal("20.00"), Decimal("120.00"))
    h = db.query(HistoricoPreco).filter_by(produto_id=produto.id).one()
    assert (h.preco, h.frete) == (Decimal("120.00"), Decimal("20.00"))


def test_frete_gratis_nao_altera_o_preco(db, produto, monkeypatch):
    html = _ld(shippingDetails={"shippingRate": {"value": 0}})
    r = _coletar(db, produto, monkeypatch, html)
    assert r.preco == Decimal("100.00") and r.frete == Decimal("0.00")


def test_frete_nao_informado_guarda_null(db, produto, monkeypatch):
    r = _coletar(db, produto, monkeypatch, _ld())
    assert r.preco == Decimal("100.00") and r.frete is None
    assert db.query(HistoricoPreco).one().frete is None


def test_frete_desligado_por_configuracao(db, produto, monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_INCLUIR_FRETE", False)
    html = _ld(shippingDetails={"shippingRate": {"value": "20.00"}})
    r = _coletar(db, produto, monkeypatch, html)
    assert r.preco == Decimal("100.00") and r.frete is None


def test_erro_ao_ler_frete_nao_invalida_a_coleta(db, produto, monkeypatch):
    def quebra(html):
        raise RuntimeError("html estranho")

    monkeypatch.setattr("app.services.coleta_service.extrair_frete", quebra)
    r = _coletar(db, produto, monkeypatch, _ld())
    assert r.coleta_valida and r.preco == Decimal("100.00") and r.frete is None


# ---------- histórico (API) e alerta ----------

def test_historico_devolve_frete(client, db, usuario, produto):
    db.add(Monitoramento(usuario_id=usuario.id, produto_id=produto.id))
    db.add(HistoricoPreco(produto_id=produto.id, preco=Decimal("120.00"), frete=Decimal("20.00")))
    db.commit()
    corpo = client.get(f"/produtos/{produto.id}/historico").json()
    assert corpo["preco_atual"] == "120.00" and corpo["frete_atual"] == "20.00"
    assert corpo["coletas"][0]["preco"] == "120.00" and corpo["coletas"][0]["frete"] == "20.00"


def test_historico_antigo_sem_frete(client, db, usuario, produto):
    db.add(Monitoramento(usuario_id=usuario.id, produto_id=produto.id))
    db.add(HistoricoPreco(produto_id=produto.id, preco=Decimal("100.00")))
    db.commit()
    corpo = client.get(f"/produtos/{produto.id}/historico").json()
    assert corpo["frete_atual"] is None and corpo["coletas"][0]["frete"] is None


@pytest.mark.parametrize(
    "frete, trecho",
    [(None, ""), (Decimal("0"), "(frete grátis)"), (Decimal("20"), "(inclui frete de R$ 20.00)")],
)
def test_mensagem_do_alerta_informa_o_frete(db, usuario, produto, frete, trecho, monkeypatch):
    monkeypatch.setattr("app.config.settings.ALERTA_SMTP_DRY_RUN", True)
    db.add(Monitoramento(usuario_id=usuario.id, produto_id=produto.id, preco_alvo=Decimal("200")))
    db.commit()
    servico = AlertaService()
    monkeypatch.setattr(servico, "_obter_email", lambda uid: "a@b.com")
    res = servico.avaliar_condicoes(
        produto, Analise(preco_atual=Decimal("120"), frete_atual=frete), db
    )
    assert len(res.alertas) == 1
    mensagem = res.alertas[0].mensagem
    assert "Preço atual: R$ 120.00" in mensagem
    assert (trecho in mensagem) if trecho else ("frete" not in mensagem)
