"""Robustez da coleta com várias lojas e registro de falhas (RF08, RN09, RN14, RNF08).

Sem internet: `requests.get` é trocado por páginas HTML fixas e o relógio do
serviço é falso, então o intervalo mínimo é conferido sem esperar de verdade.
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import requests
from sqlalchemy.exc import IntegrityError

from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.produto import Produto
from app.services import coleta_service
from app.services.ciclo_service import CicloMonitoramentoService
from app.services.coleta_service import (
    MOTIVO_HTTP,
    MOTIVO_INESPERADO,
    MOTIVO_LAYOUT,
    ColetaService,
)

URL_ML = "https://www.mercadolivre.com.br/produto-1"
URL_MAGALU = "https://www.magazineluiza.com.br/produto/p/2"

ML_OK = (
    '<html><script type="application/ld+json">'
    '{"@type":"Product","offers":{"price":"1299.90"}}</script></html>'
)
# O preço continua na página, mas a loja trocou a estrutura: nenhum seletor acha.
ML_ALTERADO = '<html><body><div class="novo-preco-v2"><span>R$ 1.299,90</span></div></body></html>'
MAGALU_OK = '<html><body><span data-testid="price-value">R$ 2.499,00</span></body></html>'
MAGALU_ALTERADO = '<html><body><span data-testid="valor-produto">R$ 2.499,00</span></body></html>'

BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)
INTERVALO = 2.0
MAX_TENTATIVAS = 3


class RespostaFalsa:
    def __init__(self, texto="", status=200):
        self.text, self.status_code = texto, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class Relogio:
    """Relógio falso: sleep só avança o tempo, sem esperar."""

    def __init__(self):
        self.agora, self.esperas = 1000.0, []

    def monotonic(self):
        return self.agora

    def sleep(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos


@pytest.fixture()
def internet(monkeypatch):
    """Páginas por URL (str -> RespostaFalsa/Exception) e o registro das chamadas."""
    paginas, chamadas, relogio = {}, [], Relogio()

    def get(url, **kwargs):
        chamadas.append(url)
        resposta = paginas[url]
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    monkeypatch.setattr(coleta_service.requests, "get", get)
    monkeypatch.setattr(
        coleta_service, "time", SimpleNamespace(monotonic=relogio.monotonic, sleep=relogio.sleep)
    )
    monkeypatch.setattr(coleta_service.settings, "COLETA_INTERVALO_MINIMO_SEGUNDOS", INTERVALO)
    monkeypatch.setattr(coleta_service.settings, "COLETA_MAX_TENTATIVAS", MAX_TENTATIVAS)
    monkeypatch.setattr(ColetaService, "_ultima_requisicao_em", 0.0)
    return SimpleNamespace(paginas=paginas, chamadas=chamadas, relogio=relogio)


@pytest.fixture()
def lojas(db):
    ml = Loja(nome="Mercado Livre", dominio="mercadolivre.com.br")
    magalu = Loja(nome="Magazine Luiza", dominio="magazineluiza.com.br")
    db.add_all([ml, magalu])
    db.commit()
    return SimpleNamespace(ml=ml, magalu=magalu)


@pytest.fixture()
def produtos(db, lojas):
    p_ml = Produto(nome="Notebook ML", url_produto=URL_ML, loja_id=lojas.ml.id)
    p_magalu = Produto(nome="TV Magalu", url_produto=URL_MAGALU, loja_id=lojas.magalu.id)
    db.add_all([p_ml, p_magalu])
    db.commit()
    return SimpleNamespace(ml=p_ml, magalu=p_magalu)


def _linhas(db, produto):
    return (
        db.query(HistoricoPreco)
        .filter(HistoricoPreco.produto_id == produto.id)
        .order_by(HistoricoPreco.data_hora_coleta)
        .all()
    )


def _por_produto(resultados):
    return {r.produto_id: r for r in resultados}


# ---------- uma loja falha, as outras seguem ----------

@pytest.mark.parametrize("quem_falha", ["ml", "magalu"])
def test_html_alterado_em_uma_loja_nao_interrompe_a_outra(db, produtos, internet, quem_falha):
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO if quem_falha == "ml" else ML_OK)
    internet.paginas[URL_MAGALU] = RespostaFalsa(
        MAGALU_ALTERADO if quem_falha == "magalu" else MAGALU_OK
    )

    resultados = _por_produto(ColetaService().executar_coleta_ativos(db))

    falhou, ok = (
        (produtos.ml, produtos.magalu) if quem_falha == "ml" else (produtos.magalu, produtos.ml)
    )
    assert resultados[falhou.id].coleta_valida is False
    assert resultados[falhou.id].motivo_falha == MOTIVO_LAYOUT
    assert resultados[ok.id].coleta_valida is True
    assert resultados[ok.id].preco in (Decimal("1299.90"), Decimal("2499.00"))

    [linha_ok] = _linhas(db, ok)
    assert linha_ok.coleta_valida is True and linha_ok.preco > 0
    [linha_falha] = _linhas(db, falhou)
    assert linha_falha.coleta_valida is False


def test_erro_de_rede_em_uma_loja_nao_interrompe_a_outra(db, produtos, internet):
    internet.paginas[URL_ML] = requests.ConnectionError("conexão recusada")
    internet.paginas[URL_MAGALU] = RespostaFalsa(MAGALU_OK)

    resultados = _por_produto(ColetaService().executar_coleta_ativos(db))

    assert resultados[produtos.ml.id].coleta_valida is False
    assert resultados[produtos.ml.id].motivo_falha == "rede"
    assert resultados[produtos.magalu.id].preco == Decimal("2499.00")


def test_excecao_inesperada_em_um_produto_nao_para_o_laco(db, produtos, internet):
    internet.paginas[URL_MAGALU] = RespostaFalsa(MAGALU_OK)
    url_que_quebra = URL_ML

    class ServicoQuebrado(ColetaService):
        def _executar_coleta(self, produto, db):
            if produto.url_produto == url_que_quebra:
                raise RuntimeError("bug inesperado")
            return super()._executar_coleta(produto, db)

    resultados = _por_produto(ServicoQuebrado().executar_coleta_ativos(db))

    assert resultados[produtos.ml.id].coleta_valida is False
    assert resultados[produtos.ml.id].motivo_falha == MOTIVO_INESPERADO
    assert resultados[produtos.magalu.id].coleta_valida is True


def test_falha_ao_gravar_a_falha_nao_derruba_os_demais(db, produtos, internet, monkeypatch):
    """Se nem o registro da falha puder ser gravado, o laço continua."""
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)
    internet.paginas[URL_MAGALU] = RespostaFalsa(MAGALU_OK)

    commit_real = db.commit

    def commit(*a, **kw):
        if any(isinstance(o, HistoricoPreco) and not o.coleta_valida for o in db.new):
            raise RuntimeError("banco indisponível")
        return commit_real(*a, **kw)

    monkeypatch.setattr(db, "commit", commit)

    resultados = _por_produto(ColetaService().executar_coleta_ativos(db))

    assert resultados[produtos.ml.id].coleta_valida is False
    assert resultados[produtos.ml.id].historico_id is None  # não conseguiu registrar
    assert resultados[produtos.magalu.id].coleta_valida is True
    assert len(_linhas(db, produtos.magalu)) == 1


# ---------- RN09 / RN14: histórico preservado, nunca preço zero ----------

def test_falha_preserva_o_historico_e_nao_grava_preco_zero(db, produtos, internet):
    for i, preco in enumerate(["100.00", "110.00"]):
        db.add(HistoricoPreco(
            produto_id=produtos.ml.id, preco=Decimal(preco), coleta_valida=True,
            data_hora_coleta=BASE + timedelta(days=i),
        ))
    db.commit()
    antes = [(h.id, h.preco) for h in _linhas(db, produtos.ml)]
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)

    resultado = ColetaService().executar_coleta(produtos.ml, db)

    assert resultado.coleta_valida is False and resultado.preco is None
    linhas = _linhas(db, produtos.ml)
    assert [(h.id, h.preco) for h in linhas[:2]] == antes  # nada apagado nem alterado
    assert len(linhas) == 3
    assert linhas[2].coleta_valida is False
    assert linhas[2].preco is None  # nem 0.00, nem cópia do último preço
    assert not [h for h in db.query(HistoricoPreco).all() if h.preco == 0]


def test_falha_sem_historico_previo_tambem_nao_grava_zero(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)

    ColetaService().executar_coleta(produtos.ml, db)

    [linha] = _linhas(db, produtos.ml)
    assert linha.coleta_valida is False
    assert linha.preco is None


def test_banco_recusa_coleta_valida_sem_preco_ou_com_preco_zero(db, produtos):
    for preco in (None, Decimal("0")):
        db.add(HistoricoPreco(produto_id=produtos.ml.id, preco=preco, coleta_valida=True))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    db.add(HistoricoPreco(produto_id=produtos.ml.id, preco=None, coleta_valida=False))
    db.commit()  # coleta inválida sem preço é o registro correto de uma falha


# ---------- log claro quando o HTML muda ----------

def test_html_alterado_gera_erro_claro_no_log(db, produtos, internet, caplog):
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)

    with caplog.at_level(logging.WARNING, logger=coleta_service.logger.name):
        resultado = ColetaService().executar_coleta(produtos.ml, db)

    erros = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(erros) == 1
    mensagem = erros[0].getMessage()
    assert "layout_alterado" in mensagem
    assert "Layout alterado?" in mensagem
    assert "Mercado Livre" in mensagem  # extrator/loja
    assert URL_ML in mensagem  # qual página
    assert "EXTRATORES" in mensagem  # onde corrigir
    assert resultado.erro and "Layout alterado?" in resultado.erro


def test_layout_alterado_de_loja_sem_extrator_usa_o_generico(db, internet):
    loja = Loja(nome="Loja X", dominio="lojax.com.br")
    db.add(loja)
    db.commit()
    produto = Produto(nome="X", url_produto="https://lojax.com.br/p/1", loja_id=loja.id)
    db.add(produto)
    db.commit()
    internet.paginas[produto.url_produto] = RespostaFalsa("<html><body>sem preço</body></html>")

    resultado = ColetaService().executar_coleta(produto, db)

    assert resultado.motivo_falha == MOTIVO_LAYOUT
    assert "genérico" in resultado.erro


# ---------- RNF08: tentativas e intervalo mínimo ----------

def test_respeita_limite_de_tentativas_e_intervalo_minimo(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)

    resultado = ColetaService().executar_coleta(produtos.ml, db)

    assert resultado.tentativas == MAX_TENTATIVAS
    assert internet.chamadas == [URL_ML] * MAX_TENTATIVAS
    # Uma espera de INTERVALO entre cada par de requisições, sem esperar em dobro.
    assert internet.relogio.esperas == [INTERVALO] * (MAX_TENTATIVAS - 1)


def test_intervalo_minimo_vale_entre_lojas_diferentes(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa(ML_OK)
    internet.paginas[URL_MAGALU] = RespostaFalsa(MAGALU_OK)

    ColetaService().executar_coleta_ativos(db)

    assert len(internet.chamadas) == 2
    assert internet.relogio.esperas == [INTERVALO]


def test_erro_404_nao_e_retentado_mas_fica_registrado(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa(status=404)

    resultado = ColetaService().executar_coleta(produtos.ml, db)

    assert internet.chamadas == [URL_ML]  # uma única requisição
    assert resultado.motivo_falha == MOTIVO_HTTP
    [linha] = _linhas(db, produtos.ml)
    assert linha.coleta_valida is False and linha.preco is None


def test_pagina_de_captcha_e_falha_de_bloqueio(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa("<html>/errors/validateCaptcha</html>")

    resultado = ColetaService().executar_coleta(produtos.ml, db)

    assert resultado.motivo_falha == "bloqueio"
    assert resultado.coleta_valida is False


# ---------- ciclo completo: loja que falha não gera análise nem alerta ----------

def test_ciclo_analisa_so_a_loja_que_coletou(db, produtos, internet):
    internet.paginas[URL_ML] = RespostaFalsa(ML_ALTERADO)
    internet.paginas[URL_MAGALU] = RespostaFalsa(MAGALU_OK)

    ciclo = CicloMonitoramentoService().executar_ciclo(db)

    itens = {i.coleta.produto_id: i for i in ciclo.produtos}
    assert len(ciclo.produtos) == 2
    assert itens[produtos.ml.id].analise is None and itens[produtos.ml.id].alertas == []
    assert itens[produtos.magalu.id].analise is not None
    assert ciclo.validas == 1
