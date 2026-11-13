"""Selenium no robô de coleta (issue #103). Nenhum teste abre um Chrome de verdade."""

from decimal import Decimal

import pytest

from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.produto import Produto
from app.seed_lojas import semear_lojas
from app.services import navegador
from app.services.coleta_service import ColetaService, _pagina_bloqueada, _precisa_navegador

HTML_BLOQUEIO = "<html><title>Just a moment...</title></html>"
HTML_OK = '<html><script type="application/ld+json">{"offers": {"price": "150.00"}}</script></html>'


class _Resposta:
    def __init__(self, texto, status=200):
        self.text = texto
        self.status_code = status

    def raise_for_status(self):
        pass


class DriverFalso:
    """Devolve `paginas` em sequência a cada leitura de page_source."""

    def __init__(self, paginas):
        self.paginas = list(paginas)
        self.urls = []
        self.fechado = False
        self.current_url = ""

    def get(self, url):
        self.urls.append(url)
        self.current_url = url

    @property
    def page_source(self):
        return self.paginas.pop(0) if len(self.paginas) > 1 else self.paginas[0]

    def quit(self):
        self.fechado = True


@pytest.fixture()
def produto(db, monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_INTERVALO_MINIMO_SEGUNDOS", 0)
    semear_lojas(db)
    loja = db.query(Loja).filter(Loja.dominio == "amazon.com.br").one()
    p = Produto(nome="X", url_produto="https://www.amazon.com.br/dp/B000", loja_id=loja.id)
    db.add(p)
    db.commit()
    return p


# ---------- detecção de bloqueio ----------

def test_marcadores_de_desafio_sao_reconhecidos():
    assert _pagina_bloqueada(HTML_BLOQUEIO)
    assert not _pagina_bloqueada(HTML_OK)


@pytest.mark.parametrize("status", [403, 429, 503])
def test_status_de_bloqueio_pede_navegador(status):
    assert _precisa_navegador(_Resposta("<html></html>", status))


def test_pagina_normal_nao_pede_navegador():
    assert not _precisa_navegador(_Resposta(HTML_OK, 200))


# ---------- navegador.buscar_pagina ----------

def test_buscar_pagina_devolve_html_renderizado_e_fecha_o_driver(monkeypatch):
    driver = DriverFalso([HTML_OK])
    r = navegador.buscar_pagina("https://loja.com.br/p", "UA", _pagina_bloqueada, lambda ua: driver)
    assert r.text == HTML_OK and driver.urls == ["https://loja.com.br/p"] and driver.fechado


def test_buscar_pagina_espera_o_desafio_se_resolver(monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS", 5)
    monkeypatch.setattr("app.services.navegador.time.sleep", lambda s: None)
    driver = DriverFalso([HTML_BLOQUEIO, HTML_BLOQUEIO, HTML_OK])
    r = navegador.buscar_pagina("https://loja.com.br/p", "UA", _pagina_bloqueada, lambda ua: driver)
    assert r.text == HTML_OK


def test_buscar_pagina_desiste_se_o_desafio_nao_sai(monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_SELENIUM_ESPERA_DESAFIO_SEGUNDOS", 0)
    driver = DriverFalso([HTML_BLOQUEIO])
    r = navegador.buscar_pagina("https://loja.com.br/p", "UA", _pagina_bloqueada, lambda ua: driver)
    assert _pagina_bloqueada(r.text) and driver.fechado


def test_buscar_pagina_fecha_o_driver_mesmo_com_erro():
    class Quebrado(DriverFalso):
        def get(self, url):
            raise RuntimeError("falhou")

    driver = Quebrado(["x"])
    with pytest.raises(RuntimeError):
        navegador.buscar_pagina("https://loja.com.br/p", "UA", _pagina_bloqueada, lambda ua: driver)
    assert driver.fechado


def test_sem_selenium_instalado_levanta_navegador_indisponivel(monkeypatch):
    import builtins

    real = builtins.__import__

    def sem_selenium(nome, *a, **k):
        if nome.startswith("selenium"):
            raise ImportError("sem selenium")
        return real(nome, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sem_selenium)
    with pytest.raises(navegador.NavegadorIndisponivel):
        navegador._criar_driver("UA")


# ---------- integração com o ColetaService ----------

def _coletar(db, produto, monkeypatch, modo, requests_resp, navegador_resp=None):
    monkeypatch.setattr("app.config.settings.COLETA_SELENIUM_MODO", modo)
    servico = ColetaService()
    chamadas = {"requests": 0, "navegador": 0}

    def _req(url):
        chamadas["requests"] += 1
        return requests_resp

    def _nav(url):
        chamadas["navegador"] += 1
        if isinstance(navegador_resp, Exception):
            raise navegador_resp
        return navegador_resp

    monkeypatch.setattr(servico, "_requisitar", _req)
    monkeypatch.setattr(servico, "_requisitar_navegador", _nav)
    return servico.executar_coleta(produto, db), chamadas


def test_modo_auto_cai_para_selenium_quando_a_loja_bloqueia(db, produto, monkeypatch):
    resultado, c = _coletar(
        db, produto, monkeypatch, "auto", _Resposta(HTML_BLOQUEIO), _Resposta(HTML_OK)
    )
    assert resultado.coleta_valida and resultado.preco == Decimal("150.00")
    assert c == {"requests": 1, "navegador": 1}


def test_modo_auto_nao_abre_navegador_se_requests_funciona(db, produto, monkeypatch):
    resultado, c = _coletar(db, produto, monkeypatch, "auto", _Resposta(HTML_OK))
    assert resultado.coleta_valida and c == {"requests": 1, "navegador": 0}


def test_modo_auto_sem_chrome_mantem_a_falha_antiga(db, produto, monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_MAX_TENTATIVAS", 1)
    resultado, c = _coletar(
        db, produto, monkeypatch, "auto", _Resposta(HTML_BLOQUEIO),
        navegador.NavegadorIndisponivel("sem chrome"),
    )
    assert resultado.coleta_valida is False and "bloqueou" in resultado.erro
    assert db.query(HistoricoPreco).filter_by(produto_id=produto.id, coleta_valida=False).count() == 1


def test_modo_desligado_nunca_usa_selenium(db, produto, monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_MAX_TENTATIVAS", 1)
    resultado, c = _coletar(db, produto, monkeypatch, "desligado", _Resposta(HTML_BLOQUEIO), _Resposta(HTML_OK))
    assert resultado.coleta_valida is False and c == {"requests": 1, "navegador": 0}


def test_modo_sempre_usa_so_o_selenium(db, produto, monkeypatch):
    resultado, c = _coletar(db, produto, monkeypatch, "sempre", _Resposta(HTML_BLOQUEIO), _Resposta(HTML_OK))
    assert resultado.coleta_valida and c == {"requests": 0, "navegador": 1}


def test_modo_invalido_vira_auto(monkeypatch):
    monkeypatch.setattr("app.config.settings.COLETA_SELENIUM_MODO", "banana")
    assert navegador.modo_selenium() == "auto"
