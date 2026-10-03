import pytest

from app.utils.urls import (
    URLInvalida, normalizar_dominio, normalizar_url_produto, url_pertence_a_loja,
)


@pytest.mark.parametrize("entrada,esperado", [
    ("kabum.com.br", "kabum.com.br"),
    ("  WWW.KaBum.com.br ", "kabum.com.br"),
    ("https://www.kabum.com.br/produto/1", "kabum.com.br"),
    ("kabum.com.br:443/x", "kabum.com.br"),
])
def test_normalizar_dominio_ok(entrada, esperado):
    assert normalizar_dominio(entrada) == esperado


@pytest.mark.parametrize("entrada", [
    "", "   ", "localhost", "loja", "127.0.0.1", "http://192.168.0.1/x",
    "loja.local", "-ruim.com", "a b.com", "loja.123",
])
def test_normalizar_dominio_invalido(entrada):
    with pytest.raises(URLInvalida):
        normalizar_dominio(entrada)


def test_normalizar_url_produto_ok():
    url = normalizar_url_produto(" HTTPS://WWW.Loja.com.br/p/mouse?sku=1#avaliacoes ")
    assert url == "https://www.loja.com.br/p/mouse?sku=1"


@pytest.mark.parametrize("entrada", [
    "", "loja.com.br/p/1", "ftp://loja.com.br/p/1", "javascript:alert(1)",
    "https://loja.com.br", "https://loja.com.br/", "http://localhost/p/1",
    "http://127.0.0.1/p/1", "http://10.0.0.5/p/1", "https://user:pw@loja.com.br/p/1",
    "https://loja.com.br:8080/p/1", "https://loja/p/1", "https://[::1]/p/1",
    "https://loja.com.br/" + "a" * 2100,
])
def test_normalizar_url_produto_invalida(entrada):
    with pytest.raises(URLInvalida):
        normalizar_url_produto(entrada)


def test_url_pertence_a_loja():
    assert url_pertence_a_loja("https://www.loja.com.br/p/1", "loja.com.br")
    assert url_pertence_a_loja("https://m.loja.com.br/p/1", "loja.com.br")
    assert not url_pertence_a_loja("https://outraloja.com.br/p/1", "loja.com.br")
    assert not url_pertence_a_loja("https://evilloja.com.br/p/1", "loja.com.br")
    assert not url_pertence_a_loja("https://loja.com.br.evil.com/p/1", "loja.com.br")
