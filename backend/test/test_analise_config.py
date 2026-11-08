"""Fase 7: limiares, mínimo de coletas e janela da média vêm da configuração."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.config import settings
from app.services.analise_service import AnaliseService, ClassificacaoQueda

BASE = datetime(2026, 10, 1, 12, 0, 0)


@dataclass
class Coleta:
    preco: Decimal
    data_hora_coleta: datetime
    coleta_valida: bool = True
    produto_id: str | None = None


def historico(precos, dias=None, **kw):
    dias = dias if dias is not None else range(len(precos))
    return [Coleta(Decimal(str(p)), BASE + timedelta(days=d), **kw) for p, d in zip(precos, dias)]


def test_padroes_da_config_sao_5_10_20_e_3():
    assert settings.ANALISE_LIMIAR_PEQUENA_PERCENTUAL == 5
    assert settings.ANALISE_LIMIAR_RELEVANTE_PERCENTUAL == 10
    assert settings.ANALISE_LIMIAR_GRANDE_PERCENTUAL == 20
    assert settings.ANALISE_MIN_COLETAS_COMPARACAO == 3
    assert settings.ANALISE_JANELA_DIAS == 30


def test_servico_le_limiares_da_config(monkeypatch):
    monkeypatch.setattr(settings, "ANALISE_LIMIAR_PEQUENA_PERCENTUAL", 2.0)
    monkeypatch.setattr(settings, "ANALISE_LIMIAR_RELEVANTE_PERCENTUAL", 4.0)
    monkeypatch.setattr(settings, "ANALISE_LIMIAR_GRANDE_PERCENTUAL", 8.0)
    servico = AnaliseService()
    esperado = {97: ClassificacaoQueda.PEQUENA, 95: ClassificacaoQueda.RELEVANTE,
                92: ClassificacaoQueda.GRANDE, 99: ClassificacaoQueda.SEM_QUEDA}
    for atual, faixa in esperado.items():
        assert servico.classificar(historico([100, 100, 100, atual])).classificacao == faixa


def test_servico_le_minimo_de_coletas_da_config(monkeypatch):
    monkeypatch.setattr(settings, "ANALISE_MIN_COLETAS_COMPARACAO", 5)
    servico = AnaliseService()
    r = servico.classificar(historico([100, 100, 100, 100, 80]))
    assert r.classificacao == ClassificacaoQueda.SEM_DADOS  # só 4 anteriores


@pytest.mark.parametrize("kwargs", [
    dict(limiar_queda_percentual=10, limiar_relevante_percentual=5),
    dict(limiar_relevante_percentual=25),                 # relevante > grande (20)
    dict(limiar_queda_percentual=0),
    dict(min_amostras_media=0),
    dict(janela_dias=-1),
])
def test_configuracao_invalida_e_recusada(kwargs):
    with pytest.raises(ValueError):
        AnaliseService(**kwargs)


def test_janela_ignora_coletas_antigas():
    # Preço antigo (200) fora da janela de 30 dias não entra na média.
    h = historico([200, 100, 100, 100, 90], dias=[0, 60, 70, 80, 85])
    r = AnaliseService(janela_dias=30).classificar(h)
    assert r.amostras_media == 3
    assert r.media_historica == Decimal("100")
    assert r.classificacao == ClassificacaoQueda.RELEVANTE


def test_janela_zero_usa_todo_o_historico():
    h = historico([200, 100, 100, 100, 90], dias=[0, 60, 70, 80, 85])
    r = AnaliseService(janela_dias=0).classificar(h)
    assert r.amostras_media == 4
    assert r.media_historica == Decimal("125")


def test_janela_com_poucas_coletas_recentes_da_sem_dados():
    h = historico([100, 100, 100, 100, 90], dias=[0, 1, 2, 3, 80])
    r = AnaliseService(janela_dias=30).classificar(h)
    assert r.classificacao == ClassificacaoQueda.SEM_DADOS
    assert AnaliseService(janela_dias=30).comparar_com_media(h) is None


def test_janela_e_ancorada_na_coleta_mais_recente_e_inclui_o_limite():
    h = historico([100, 100, 100, 90], dias=[0, 10, 20, 30])  # a 1ª está exatamente a 30 dias
    assert AnaliseService(janela_dias=30).classificar(h).amostras_media == 3


def test_coletas_invalidas_nao_entram_na_janela_nem_na_media():
    h = historico([100, 100, 100, 100, 90])
    h[1].coleta_valida = False
    h[3].preco = Decimal("0")
    r = AnaliseService().classificar(h)
    assert r.amostras_media == 2 and r.classificacao == ClassificacaoQueda.SEM_DADOS


def test_historico_de_dois_produtos_e_recusado():
    h = historico([100, 100, 100, 90], produto_id="a")
    h[1].produto_id = "b"
    with pytest.raises(ValueError):
        AnaliseService().classificar(h)


def test_mesmo_produto_passa():
    h = historico([100, 100, 100, 90], produto_id="a")
    assert AnaliseService().classificar(h).classificacao == ClassificacaoQueda.RELEVANTE
