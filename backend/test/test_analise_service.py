from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.analise_service import AnaliseService, ClassificacaoQueda

BASE = datetime(2026, 10, 1, 12, 0, 0)


@dataclass
class Coleta:
    """Dublê simples de HistoricoPreco, sem precisar do banco."""
    preco: Decimal
    data_hora_coleta: datetime
    coleta_valida: bool = True


def montar_historico(precos, invalidos_em=()):
    """Gera coletas em dias sucessivos a partir de BASE; `invalidos_em`
    marca índices como coleta_valida=False (simula falhas de scraping)."""
    return [
        Coleta(
            preco=Decimal(str(p)),
            data_hora_coleta=BASE + timedelta(days=i),
            coleta_valida=i not in invalidos_em,
        )
        for i, p in enumerate(precos)
    ]


@pytest.fixture()
def servico():
    return AnaliseService()  # limiar=5%, min_amostras_media=3 (padrões)


# ---------- comparar_com_coleta_anterior (RF12) ----------

def test_comparar_com_coleta_anterior(servico):
    historico = montar_historico([100, 90])
    assert servico.comparar_com_coleta_anterior(historico) == pytest.approx(10.0)


def test_comparar_com_coleta_anterior_sem_historico(servico):
    assert servico.comparar_com_coleta_anterior(montar_historico([100])) is None
    assert servico.comparar_com_coleta_anterior([]) is None


def test_comparar_com_coleta_anterior_alta_de_preco(servico):
    historico = montar_historico([100, 110])
    assert servico.comparar_com_coleta_anterior(historico) == pytest.approx(-10.0)


# ---------- comparar_com_media (RF12, RN10) ----------

def test_comparar_com_media_amostras_insuficientes(servico):
    # Só 2 coletas anteriores; o padrão exige 3.
    historico = montar_historico([100, 100, 90])
    assert servico.comparar_com_media(historico) is None


def test_comparar_com_media_ok(servico):
    historico = montar_historico([100, 100, 100, 90])  # média dos 3 primeiros = 100
    assert servico.comparar_com_media(historico) == pytest.approx(10.0)


# ---------- classificar (UC11, RN06, RN09, RN10) ----------

def test_classificar_sem_dados_suficientes(servico):
    historico = montar_historico([100, 90])  # só 1 coleta anterior
    resultado = servico.classificar(historico)
    assert resultado.classificacao == ClassificacaoQueda.SEM_DADOS
    assert resultado.media_historica is None
    assert resultado.queda_relevante is False


def test_classificar_sem_queda_preco_subiu(servico):
    historico = montar_historico([100, 100, 100, 110])
    resultado = servico.classificar(historico)
    assert resultado.classificacao == ClassificacaoQueda.SEM_QUEDA


def test_classificar_variacao_abaixo_do_limiar_nao_e_queda(servico):
    # 4a: variação de 4% (< 5%) não é classificada como queda.
    historico = montar_historico([100, 100, 100, 96])
    resultado = servico.classificar(historico)
    assert resultado.classificacao == ClassificacaoQueda.SEM_QUEDA
    assert resultado.variacao_percentual_media == pytest.approx(4.0)


@pytest.mark.parametrize("preco_atual,esperado", [
    (95, ClassificacaoQueda.PEQUENA),   # 5%
    (91, ClassificacaoQueda.PEQUENA),   # 9%
    (90, ClassificacaoQueda.RELEVANTE), # 10%
    (81, ClassificacaoQueda.RELEVANTE), # 19%
    (80, ClassificacaoQueda.GRANDE),    # 20%
    (50, ClassificacaoQueda.GRANDE),    # 50%
])
def test_classificar_faixas_de_queda(servico, preco_atual, esperado):
    historico = montar_historico([100, 100, 100, preco_atual])
    assert servico.classificar(historico).classificacao == esperado


def test_queda_relevante_so_vale_para_relevante_e_grande(servico):
    pequena = servico.classificar(montar_historico([100, 100, 100, 92]))
    relevante = servico.classificar(montar_historico([100, 100, 100, 85]))
    grande = servico.classificar(montar_historico([100, 100, 100, 70]))
    assert pequena.queda_relevante is False
    assert relevante.queda_relevante is True
    assert grande.queda_relevante is True


def test_identificar_queda_relevante_atalho_booleano(servico):
    historico = montar_historico([100, 100, 100, 85])
    assert servico.identificar_queda_relevante(historico) is True


def test_classificar_ignora_coletas_invalidas(servico):
    # RN09: a coleta inválida (índice 2, preço 1) não deve contaminar a média.
    historico = montar_historico([100, 100, 1, 100, 90], invalidos_em={2})
    resultado = servico.classificar(historico)
    assert resultado.amostras_media == 3  # as 3 coletas válidas de 100
    assert resultado.media_historica == Decimal("100")
    assert resultado.classificacao == ClassificacaoQueda.RELEVANTE


def test_classificar_historico_vazio_levanta_erro(servico):
    with pytest.raises(ValueError):
        servico.classificar([])


def test_limiar_e_minimo_de_amostras_sao_configuraveis():
    servico = AnaliseService(limiar_queda_percentual=10.0, min_amostras_media=1)
    historico = montar_historico([100, 93])  # 1 amostra anterior, variação de 7%
    resultado = servico.classificar(historico)
    # Com min_amostras_media=1, já há dados suficientes.
    assert resultado.classificacao != ClassificacaoQueda.SEM_DADOS
    # Com limiar de 10%, 7% de queda não é considerado queda.
    assert resultado.classificacao == ClassificacaoQueda.SEM_QUEDA
