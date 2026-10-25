"""Extratores de preço por loja e identificação de domínio (issue #67, RF07)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.loja import Loja
from app.seed_lojas import LOJAS_MVP, semear_lojas
from app.services.coleta_service import (
    ColetaService,
    extrair_preco,
    identificar_dominio,
    selecionar_extrator,
)

JSON_LD = (
    '<script type="application/ld+json">'
    '{"@type":"Product","offers":{"@type":"Offer","price":"1299.90"}}</script>'
)

HTML_MAGALU_SELETOR = '<p data-testid="price-value">R$ 2.499,00</p>'
HTML_AMAZON = (
    '<div id="corePrice_feature_div"><span class="a-price">'
    '<span class="a-offscreen">R$ 349,90</span></span></div>'
)
HTML_KABUM = '<h4 class="finalPrice">R$ 1.899,99</h4>'


@pytest.mark.parametrize("dominio,nome", [
    ("mercadolivre.com.br", "Mercado Livre"),
    ("produto.mercadolivre.com.br", "Mercado Livre"),
    ("magazineluiza.com.br", "Magazine Luiza"),
    ("amazon.com.br", "Amazon BR"),
    ("kabum.com.br", "Kabum"),
    ("books.toscrape.com", "Books to Scrape (demo)"),
    ("www.magazineluiza.com.br", "Magazine Luiza"),
])
def test_selecionar_extrator_por_dominio(dominio, nome):
    assert selecionar_extrator(dominio).nome == nome


def test_dominio_desconhecido_usa_fallback_generico():
    assert selecionar_extrator("lojaqualquer.com.br") is None
    assert extrair_preco(JSON_LD, "lojaqualquer.com.br") == Decimal("1299.90")


@pytest.mark.parametrize("dominio", ["magazineluiza.com.br", "amazon.com.br", "kabum.com.br"])
def test_json_ld_funciona_nas_lojas_novas(dominio):
    assert extrair_preco(f"<html>{JSON_LD}</html>", dominio) == Decimal("1299.90")


@pytest.mark.parametrize("dominio,html,esperado", [
    ("magazineluiza.com.br", HTML_MAGALU_SELETOR, Decimal("2499.00")),
    ("amazon.com.br", HTML_AMAZON, Decimal("349.90")),
    ("kabum.com.br", HTML_KABUM, Decimal("1899.99")),
])
def test_seletor_da_pagina_nas_lojas_novas(dominio, html, esperado):
    assert extrair_preco(f"<html><body>{html}</body></html>", dominio) == esperado


@pytest.mark.parametrize("dominio", ["magazineluiza.com.br", "amazon.com.br", "kabum.com.br"])
def test_pagina_sem_preco_devolve_none(dominio):
    assert extrair_preco("<html><body>nada aqui</body></html>", dominio) is None


def test_extrator_de_uma_loja_nao_vaza_para_outra():
    # Seletor da Kabum não deve ser lido numa página do Mercado Livre.
    assert extrair_preco(f"<html>{HTML_KABUM}</html>", "mercadolivre.com.br") is None


def test_identificar_dominio_usa_loja_cadastrada():
    produto = SimpleNamespace(url_produto="https://www.outro.com/p/1")
    loja = SimpleNamespace(dominio="Magazineluiza.com.br")
    assert identificar_dominio(produto, loja) == "magazineluiza.com.br"


def test_identificar_dominio_sem_loja_usa_hostname_sem_www():
    produto = SimpleNamespace(url_produto="https://www.kabum.com.br/produto/123/placa")
    assert identificar_dominio(produto, None) == "kabum.com.br"


def test_lojas_do_mvp_tem_extrator_ou_sao_explicitas():
    for _nome, dominio in LOJAS_MVP:
        assert selecionar_extrator(dominio) is not None, dominio


def test_semear_lojas_e_idempotente(db):
    criadas = semear_lojas(db)
    assert len(criadas) == len(LOJAS_MVP)
    assert semear_lojas(db) == []
    assert db.query(Loja).count() == len(LOJAS_MVP)


def test_semear_nao_duplica_loja_ja_cadastrada(db):
    db.add(Loja(nome="Magalu", dominio="magazineluiza.com.br"))
    db.commit()
    criadas = semear_lojas(db)
    assert len(criadas) == len(LOJAS_MVP) - 1
    assert db.query(Loja).filter(Loja.dominio == "magazineluiza.com.br").count() == 1


class _Resposta:
    def __init__(self, texto, status=200):
        self.text = texto
        self.status_code = status

    def raise_for_status(self):
        pass


def test_executar_coleta_magalu_grava_historico(db, monkeypatch):
    """Ponta a ponta do robô: Loja Magalu no banco -> extrator certo -> histórico."""
    from app.models.historico_preco import HistoricoPreco
    from app.models.produto import Produto

    semear_lojas(db)
    loja = db.query(Loja).filter(Loja.dominio == "magazineluiza.com.br").one()
    produto = Produto(
        nome="Fone", url_produto="https://www.magazineluiza.com.br/fone/p/1/", loja_id=loja.id
    )
    db.add(produto)
    db.commit()

    servico = ColetaService()
    monkeypatch.setattr(
        servico, "_requisitar", lambda url: _Resposta(f"<html>{HTML_MAGALU_SELETOR}</html>")
    )
    resultado = servico.executarColeta(produto, db)

    assert resultado.coleta_valida and resultado.preco == Decimal("2499.00")
    assert db.query(HistoricoPreco).filter_by(produto_id=produto.id).one().preco == Decimal("2499.00")


def test_pagina_de_captcha_da_amazon_e_falha(db, monkeypatch):
    from app.models.produto import Produto

    semear_lojas(db)
    loja = db.query(Loja).filter(Loja.dominio == "amazon.com.br").one()
    produto = Produto(nome="X", url_produto="https://www.amazon.com.br/dp/B000", loja_id=loja.id)
    db.add(produto)
    db.commit()

    monkeypatch.setattr("app.config.settings.COLETA_INTERVALO_MINIMO_SEGUNDOS", 0)
    servico = ColetaService()
    monkeypatch.setattr(
        servico,
        "_requisitar",
        lambda url: _Resposta("<form action='/errors/validateCaptcha'>Digite os caracteres</form>"),
    )
    resultado = servico.executar_coleta(produto, db)
    assert resultado.coleta_valida is False
    assert "bloqueou" in resultado.erro
