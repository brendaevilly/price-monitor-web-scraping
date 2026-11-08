"""Critério de aceite RN06–RN08 da especificação.

RN06  faixas de queda: pequena 5–9,99%, relevante 10–19,99%, grande >= 20%
      (limites exatos), comparação com a coleta anterior e com a média da janela;
RN07  alerta por queda mínima (5%) e por preço-alvo (<=);
RN08  intervalo de reenvio do alerta (anti-spam).
Também cobre RN09/RN10: histórico insuficiente, coleta inválida e produtos distintos.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.config import settings
from app.models.alerta import Alerta
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.services.alerta_service import Analise, AlertaService, TIPO_PRECO_ALVO, TIPO_QUEDA
from app.services.analise_service import AnaliseService, ClassificacaoQueda

BASE = datetime(2026, 10, 1, 12, 0, 0)
C = ClassificacaoQueda


@dataclass
class Coleta:
    preco: Decimal
    data_hora_coleta: datetime
    coleta_valida: bool = True
    produto_id: str | None = None


def historico(precos, dias=None, invalidos_em=(), produto_id=None):
    dias = dias if dias is not None else range(len(precos))
    return [
        Coleta(Decimal(str(p)), BASE + timedelta(days=d), i not in invalidos_em, produto_id)
        for i, (p, d) in enumerate(zip(precos, dias))
    ]


@pytest.fixture()
def servico():
    # Padrões do projeto: 5 / 10 / 20 %, mínimo 3 coletas, janela 30 dias.
    return AnaliseService(
        limiar_queda_percentual=5, limiar_relevante_percentual=10,
        limiar_grande_percentual=20, min_amostras_media=3, janela_dias=30,
    )


# =========================== RN06: faixas e limites ===========================

# (percentual de queda, faixa esperada). Preço de referência 100 e 200 (média
# das coletas anteriores): os limites têm de valer independentemente da escala.
LIMITES = [
    ("4.99", C.SEM_QUEDA),
    ("5", C.PEQUENA),
    ("9.99", C.PEQUENA),
    ("10", C.RELEVANTE),
    ("19.99", C.RELEVANTE),
    ("20", C.GRANDE),
]


@pytest.mark.parametrize("referencia", [100, 200])
@pytest.mark.parametrize("queda,esperado", LIMITES)
def test_rn06_limites_exatos_das_faixas(servico, referencia, queda, esperado):
    atual = Decimal(referencia) * (Decimal(100) - Decimal(queda)) / Decimal(100)
    r = servico.classificar(historico([referencia] * 3 + [atual]))
    assert r.variacao_percentual_media == pytest.approx(float(queda))
    assert r.classificacao == esperado


def test_rn06_queda_relevante_comeca_em_10_por_cento(servico):
    abaixo = servico.classificar(historico([100, 100, 100, "90.01"]))
    no_limite = servico.classificar(historico([100, 100, 100, 90]))
    assert abaixo.queda_relevante is False
    assert no_limite.queda_relevante is True


def test_rn06_alta_de_preco_e_preco_igual_nao_sao_queda(servico):
    assert servico.classificar(historico([100, 100, 100, 100])).classificacao == C.SEM_QUEDA
    assert servico.classificar(historico([100, 100, 100, 130])).classificacao == C.SEM_QUEDA


def test_rn06_limiares_vem_da_configuracao_e_nao_do_codigo():
    servico = AnaliseService(
        limiar_queda_percentual=2, limiar_relevante_percentual=4, limiar_grande_percentual=8,
    )
    esperado = [("98", C.PEQUENA), ("96", C.RELEVANTE), ("92", C.GRANDE), ("99", C.SEM_QUEDA)]
    for atual, faixa in esperado:
        assert servico.classificar(historico([100, 100, 100, atual])).classificacao == faixa


# ============ RN06: coleta anterior x média da janela =========================

def test_rn06_compara_com_a_coleta_anterior_e_com_a_media(servico):
    # anteriores: 120, 100, 100, 100 -> média 105; coleta imediatamente anterior: 100.
    h = historico([120, 100, 100, 100, 90])
    assert servico.comparar_com_coleta_anterior(h) == pytest.approx(10.0)
    assert servico.comparar_com_media(h) == pytest.approx((105 - 90) / 105 * 100)
    r = servico.classificar(h)
    assert r.variacao_percentual_anterior == pytest.approx(10.0)
    assert r.variacao_percentual_media == pytest.approx(14.2857, abs=1e-3)
    # A faixa é decidida pela média (UC11), não pela coleta anterior.
    assert r.classificacao == C.RELEVANTE


def test_rn06_classificacao_segue_a_media_mesmo_se_a_anterior_cair_pouco(servico):
    # Caiu só 2% em relação à coleta anterior (98), mas 20% abaixo da média (125).
    h = historico([150, 150, 150, 100, 98])
    r = servico.classificar(h)
    assert r.variacao_percentual_anterior == pytest.approx(2.0)
    assert r.classificacao == C.GRANDE


def test_rn06_media_considera_apenas_a_janela(servico):
    # O preço de 200 está a 60 dias da coleta mais recente: fora da janela de 30 dias.
    h = historico([200, 100, 100, 100, 90], dias=[0, 60, 70, 80, 85])
    r = servico.classificar(h)
    assert r.amostras_media == 3 and r.media_historica == Decimal("100")
    assert r.variacao_percentual_media == pytest.approx(10.0)
    assert r.classificacao == C.RELEVANTE
    # Sem janela (0), o 200 entra na média e a queda passa a ser de 28%.
    todo = servico.classificar(h, janela_dias=0)
    assert todo.media_historica == Decimal("125")
    assert todo.classificacao == C.GRANDE


def test_rn06_coletas_dentro_da_janela_incluem_o_limite_de_dias(servico):
    h = historico([100, 100, 100, 90], dias=[0, 10, 20, 30])  # a 1ª está a exatos 30 dias
    assert servico.classificar(h).amostras_media == 3


# ============================ RN10: sem_dados =================================

@pytest.mark.parametrize("anteriores", [0, 1, 2])
def test_rn10_historico_insuficiente_e_sem_dados_e_nao_classifica_queda(servico, anteriores):
    # Mesmo com queda de 50%: sem o mínimo de coletas não se classifica.
    r = servico.classificar(historico([100] * anteriores + [50]))
    assert r.classificacao == C.SEM_DADOS
    assert r.media_historica is None
    assert r.variacao_percentual_media is None
    assert r.queda_relevante is False
    assert servico.comparar_com_media(historico([100] * anteriores + [50])) is None


def test_rn10_com_o_minimo_exato_ja_classifica(servico):
    assert servico.classificar(historico([100, 100, 100, 50])).classificacao == C.GRANDE


def test_rn10_janela_que_deixa_menos_que_o_minimo_da_sem_dados(servico):
    h = historico([100, 100, 100, 50], dias=[0, 1, 2, 40])  # só o preço atual está na janela
    assert servico.classificar(h).classificacao == C.SEM_DADOS


def test_rn10_sem_coleta_valida_nao_ha_o_que_analisar(servico):
    with pytest.raises(ValueError):
        servico.classificar([])
    with pytest.raises(ValueError):
        servico.classificar(historico([100, 100], invalidos_em={0, 1}))


# ============================ RN09: coleta inválida ===========================

def test_rn09_coleta_invalida_nao_entra_na_media(servico):
    h = historico([100, 100, 1, 100, 90], invalidos_em={2})
    r = servico.classificar(h)
    assert r.amostras_media == 3 and r.media_historica == Decimal("100")
    assert r.classificacao == C.RELEVANTE


def test_rn09_coleta_invalida_nao_e_o_preco_atual(servico):
    # A última coleta falhou (preço 1): o preço atual continua sendo o da última válida.
    h = historico([100, 100, 100, 95, 1], invalidos_em={4})
    r = servico.classificar(h)
    assert r.preco_atual == Decimal("95")
    assert r.classificacao == C.PEQUENA


def test_rn09_coleta_invalida_nao_conta_para_o_minimo(servico):
    # 4 coletas, mas uma inválida: sobram só 2 anteriores válidas.
    h = historico([100, 100, 100, 50], invalidos_em={1})
    assert servico.classificar(h).classificacao == C.SEM_DADOS


def test_rn09_preco_zero_ou_nulo_e_ignorado(servico):
    h = historico([100, 100, 100, 100, 90])
    h[1].preco = Decimal("0")
    h[2].preco = None
    r = servico.classificar(h)
    assert r.amostras_media == 2 and r.classificacao == C.SEM_DADOS


# ===================== RN10: produtos distintos sem mistura ===================

def test_rn10_servico_recusa_historico_de_mais_de_um_produto(servico):
    h = historico([100, 100, 100, 90], produto_id="a")
    h[1].produto_id = "b"
    with pytest.raises(ValueError):
        servico.classificar(h)


def test_rn10_cada_produto_tem_suas_proprias_estatisticas(client, db):
    """Dois produtos com preços de escalas diferentes: a média e a faixa de um
    não podem ser contaminadas pelas coletas do outro."""
    loja = client.post("/lojas", json={"nome": "KaBuM!", "dominio": "kabum.com.br"}).json()["id"]

    def cadastrar(slug):
        r = client.post("/produtos", json={
            "nome": slug, "url_produto": f"https://www.kabum.com.br/produto/{slug}", "loja_id": loja,
        })
        return r.json()["produto_id"]

    caro, barato = cadastrar("caro"), cadastrar("barato")
    for pid, precos in ((caro, [1000, 1000, 1000, 800]), (barato, [10, 10, 10, 10])):
        for i, p in enumerate(precos):
            db.add(HistoricoPreco(
                produto_id=uuid.UUID(pid), preco=Decimal(p),
                data_hora_coleta=datetime(2026, 1, 1 + i, tzinfo=timezone.utc),
            ))
    db.commit()

    por_id = {p["produto_id"]: p for p in client.get("/analise/resumo").json()["produtos"]}
    assert por_id[caro]["media_historica"] == "1000.00" and por_id[caro]["classificacao"] == "grande_queda"
    assert por_id[caro]["menor_preco"] == "800.00"
    assert por_id[barato]["media_historica"] == "10.00" and por_id[barato]["classificacao"] == "sem_queda"
    assert por_id[barato]["menor_preco"] == "10.00"
    # A rota individual concorda com o resumo.
    individual = client.get(f"/produtos/{barato}/analise").json()
    assert individual["media_historica"] == "10.00" and individual["classificacao"] == "sem_queda"


# =================== RN07 e RN08: alertas (AlertaService) =====================

@pytest.fixture()
def produto(db):
    loja = Loja(nome="Loja", dominio="loja.com.br")
    db.add(loja)
    db.commit()
    p = Produto(nome="Notebook", url_produto="https://loja.com.br/p/1", loja_id=loja.id)
    db.add(p)
    db.commit()
    return p


@pytest.fixture()
def emails(monkeypatch):
    """Dublê do SMTP: guarda (tipo, destinatário) de cada e-mail 'enviado'."""
    enviados = []
    monkeypatch.setattr(AlertaService, "_obter_email", lambda self, uid: "ana@example.com")
    monkeypatch.setattr(
        AlertaService, "enviar_email",
        lambda self, alerta, dest, produto, nome=None: enviados.append((alerta.tipo, dest)),
    )
    return enviados


def _monitorar(db, usuario, produto, preco_alvo=None, alerta_ativo=True):
    m = Monitoramento(usuario_id=usuario.id, produto_id=produto.id,
                      preco_alvo=preco_alvo, alerta_ativo=alerta_ativo)
    db.add(m)
    db.commit()
    return m


def _avaliar(db, produto, preco, queda=None):
    analise = Analise(
        preco_atual=Decimal(str(preco)),
        queda_percentual=None if queda is None else Decimal(str(queda)),
    )
    return AlertaService().avaliar_condicoes(produto, analise, db)


def _alerta_antigo(db, usuario, produto, tipo, horas_atras):
    db.add(Alerta(
        produto_id=produto.id, usuario_id=usuario.id, tipo=tipo, mensagem="antigo",
        data_envio=datetime.now(timezone.utc) - timedelta(hours=horas_atras),
    ))
    db.commit()


# ---- RN07: preço-alvo ----

@pytest.mark.parametrize("preco,dispara", [
    ("200.01", False),   # acima do alvo
    ("200.00", True),    # exatamente no alvo
    ("150.00", True),    # abaixo do alvo
])
def test_rn07_preco_alvo_dispara_quando_preco_menor_ou_igual(db, usuario, produto, emails, preco, dispara):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    r = _avaliar(db, produto, preco)
    assert [a.tipo for a in r.alertas] == ([TIPO_PRECO_ALVO] if dispara else [])
    assert emails == ([(TIPO_PRECO_ALVO, "ana@example.com")] if dispara else [])


def test_rn07_sem_preco_alvo_nao_dispara(db, usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=None)
    assert _avaliar(db, produto, "1.00").alertas == [] and emails == []


def test_rn07_alerta_desativado_nao_envia(db, usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"), alerta_ativo=False)
    assert _avaliar(db, produto, "100").alertas == [] and emails == []


# ---- RN07: queda mínima de 5% ----

@pytest.mark.parametrize("queda,dispara", [("4.99", False), ("5", True), ("12", True)])
def test_rn07_queda_minima_de_5_por_cento(db, usuario, produto, emails, queda, dispara):
    _monitorar(db, usuario, produto)  # sem preço-alvo: só a queda pode disparar
    r = _avaliar(db, produto, "90", queda=queda)
    assert [a.tipo for a in r.alertas] == ([TIPO_QUEDA] if dispara else [])
    assert len(emails) == (1 if dispara else 0)


def test_rn07_queda_e_preco_alvo_geram_um_alerta_de_cada_tipo(db, usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("95"))
    r = _avaliar(db, produto, "90", queda=10)
    assert sorted(a.tipo for a in r.alertas) == sorted([TIPO_QUEDA, TIPO_PRECO_ALVO])
    assert len(emails) == 2


def test_rn07_limiar_de_queda_vem_da_configuracao(db, usuario, produto, emails, monkeypatch):
    monkeypatch.setattr(settings, "ALERTA_QUEDA_MINIMA_PERCENTUAL", 8.0)
    _monitorar(db, usuario, produto)
    assert _avaliar(db, produto, "90", queda="7.99").alertas == []
    assert len(_avaliar(db, produto, "90", queda="8").alertas) == 1


# ---- RN08: intervalo de reenvio ----

def test_rn08_nao_reenvia_a_mesma_ocorrencia_dentro_do_intervalo(db, usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    primeira = _avaliar(db, produto, "150")
    segunda = _avaliar(db, produto, "150")
    assert len(primeira.alertas) == 1 and primeira.ignorados == 0
    assert segunda.alertas == [] and segunda.ignorados == 1
    assert len(emails) == 1
    assert db.query(Alerta).count() == 1


def test_rn08_dentro_das_24h_ignora_e_depois_delas_reenvia(db, usuario, produto, emails):
    assert settings.ALERTA_INTERVALO_REENVIOS_HORAS == 24  # padrão
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))

    _alerta_antigo(db, usuario, produto, TIPO_PRECO_ALVO, horas_atras=23)
    assert _avaliar(db, produto, "150").ignorados == 1 and emails == []

    db.query(Alerta).delete()
    _alerta_antigo(db, usuario, produto, TIPO_PRECO_ALVO, horas_atras=25)
    assert len(_avaliar(db, produto, "150").alertas) == 1 and len(emails) == 1


def test_rn08_intervalo_e_configuravel(db, usuario, produto, emails, monkeypatch):
    monkeypatch.setattr(settings, "ALERTA_INTERVALO_REENVIOS_HORAS", 48)
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    _alerta_antigo(db, usuario, produto, TIPO_PRECO_ALVO, horas_atras=30)  # < 48h
    assert _avaliar(db, produto, "150").alertas == []
    monkeypatch.setattr(settings, "ALERTA_INTERVALO_REENVIOS_HORAS", 12)    # 30h > 12h
    assert len(_avaliar(db, produto, "150").alertas) == 1


def test_rn08_o_intervalo_vale_por_tipo_de_alerta(db, usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    _alerta_antigo(db, usuario, produto, TIPO_QUEDA, horas_atras=1)  # queda já enviada
    r = _avaliar(db, produto, "150", queda=10)
    # A queda é bloqueada; o preço-alvo (outro tipo) ainda não foi enviado.
    assert [a.tipo for a in r.alertas] == [TIPO_PRECO_ALVO]
    assert r.ignorados == 1


def test_rn08_o_intervalo_vale_por_usuario(db, usuario, outro_usuario, produto, emails):
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    _monitorar(db, outro_usuario, produto, preco_alvo=Decimal("200"))
    _alerta_antigo(db, usuario, produto, TIPO_PRECO_ALVO, horas_atras=1)
    r = _avaliar(db, produto, "150")
    assert [a.usuario_id for a in r.alertas] == [outro_usuario.id]
    assert r.ignorados == 1


def test_rn08_o_intervalo_vale_por_produto(db, usuario, produto, emails):
    outro = Produto(nome="Outro", url_produto="https://loja.com.br/p/2", loja_id=produto.loja_id)
    db.add(outro)
    db.commit()
    _monitorar(db, usuario, produto, preco_alvo=Decimal("200"))
    _monitorar(db, usuario, outro, preco_alvo=Decimal("200"))
    _alerta_antigo(db, usuario, outro, TIPO_PRECO_ALVO, horas_atras=1)
    assert len(_avaliar(db, produto, "150").alertas) == 1  # o do outro produto não bloqueia