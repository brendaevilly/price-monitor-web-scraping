"""Ciclo coleta -> análise -> alerta (issue #66, RN09)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.alerta import Alerta
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.scheduler import executar_coleta_periodica
from app.services.alerta_service import AlertaService
from app.services.ciclo_service import CicloMonitoramentoService
from app.services.coleta_service import ColetaService, ResultadoColeta

BASE = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def produto(db):
    loja = Loja(nome="Loja", dominio="loja.com.br")
    db.add(loja)
    db.commit()
    p = Produto(nome="Notebook", url_produto="https://loja.com.br/p/1", loja_id=loja.id)
    db.add(p)
    db.commit()
    return p


def _historico(db, produto, precos, validos=None):
    """Insere coletas em dias sucessivos (datas explícitas, sem depender do relógio)."""
    for i, preco in enumerate(precos):
        db.add(HistoricoPreco(
            produto_id=produto.id,
            preco=Decimal(str(preco)),
            data_hora_coleta=BASE + timedelta(days=i),
            coleta_valida=True if validos is None else validos[i],
        ))
    db.commit()


class ColetaFalsa(ColetaService):
    """Em vez de ir à internet, grava o próximo preço (ou uma falha) no histórico."""

    def __init__(self, preco, valida=True, quando=None):
        self.preco, self.valida, self.quando = preco, valida, quando

    def executar_coleta(self, produto, db=None):
        h = HistoricoPreco(
            produto_id=produto.id,
            preco=Decimal(str(self.preco)),
            data_hora_coleta=self.quando or BASE + timedelta(days=30),
            coleta_valida=self.valida,
        )
        db.add(h)
        db.commit()
        db.refresh(h)
        return ResultadoColeta(
            sucesso=self.valida, produto_id=produto.id,
            preco=Decimal(str(self.preco)) if self.valida else None,
            coleta_valida=self.valida, tentativas=1, historico_id=h.id,
            erro=None if self.valida else "falha simulada",
        )


class AlertaEspiao(AlertaService):
    def __init__(self):
        self.chamadas = []

    def avaliar_condicoes(self, produto, analise, db=None):
        self.chamadas.append(analise)
        return super().avaliar_condicoes(produto, analise, db)


@pytest.fixture()
def smtp_falso(monkeypatch):
    enviados = []
    monkeypatch.setattr(AlertaService, "_obter_email", lambda self, uid: "ana@example.com")
    monkeypatch.setattr(
        AlertaService, "enviar_email",
        lambda self, alerta, dest, produto, nome=None: enviados.append((alerta.tipo, dest)),
    )
    return enviados


def _monitorar(db, usuario, produto, preco_alvo=None):
    m = Monitoramento(usuario_id=usuario.id, produto_id=produto.id, preco_alvo=preco_alvo)
    db.add(m)
    db.commit()
    return m


def test_coleta_valida_com_queda_dispara_analise_e_email(db, produto, usuario, smtp_falso):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)

    ciclo = CicloMonitoramentoService(coleta=ColetaFalsa(80), alerta=AlertaEspiao()).executar_ciclo(db)

    item = ciclo.produtos[0]
    assert item.analise.classificacao.value == "grande_queda"
    assert [t for t, _ in smtp_falso] == ["queda_preco"]
    assert len(item.alertas) == 1
    assert db.query(Alerta).count() == 1
    assert (ciclo.validas, ciclo.analisados, ciclo.alertas_enviados) == (1, 1, 1)


def test_coleta_invalida_nao_dispara_analise_nem_alerta(db, produto, usuario, smtp_falso):
    """RN09."""
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, preco_alvo=Decimal("90"))
    espiao = AlertaEspiao()

    ciclo = CicloMonitoramentoService(coleta=ColetaFalsa(1, valida=False), alerta=espiao).executar_ciclo(db)

    item = ciclo.produtos[0]
    assert item.analise is None and item.alertas == []
    assert espiao.chamadas == []
    assert smtp_falso == []
    assert db.query(Alerta).count() == 0
    # histórico anterior preservado
    assert db.query(HistoricoPreco).filter_by(produto_id=produto.id).count() == 4


def test_historico_curto_ainda_alerta_por_queda_da_coleta_anterior(db, produto, usuario, smtp_falso):
    # Só 1 coleta antes: sem média (RN10), mas queda de 20% vs anterior vale pela RN07.
    _historico(db, produto, [100])
    _monitorar(db, usuario, produto)
    espiao = AlertaEspiao()

    ciclo = CicloMonitoramentoService(coleta=ColetaFalsa(80), alerta=espiao).executar_ciclo(db)

    assert ciclo.produtos[0].analise.classificacao.value == "sem_dados"
    assert espiao.chamadas[0].preco_anterior == Decimal("100.00")
    assert [t for t, _ in smtp_falso] == ["queda_preco"]


def test_preco_alvo_atingido_dispara_alerta(db, produto, usuario, smtp_falso):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, preco_alvo=Decimal("99"))

    CicloMonitoramentoService(coleta=ColetaFalsa(98)).executar_ciclo(db)

    # queda de só 2%: apenas o preço-alvo dispara
    assert [t for t, _ in smtp_falso] == ["preco_alvo"]


def test_sem_queda_nem_alvo_nao_envia(db, produto, usuario, smtp_falso):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, preco_alvo=Decimal("50"))

    ciclo = CicloMonitoramentoService(coleta=ColetaFalsa(101)).executar_ciclo(db)

    assert smtp_falso == []
    assert ciclo.produtos[0].analise.classificacao.value == "sem_queda"


def test_anti_spam_nao_reenvia_no_ciclo_seguinte(db, produto, usuario, smtp_falso):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)

    CicloMonitoramentoService(coleta=ColetaFalsa(80)).executar_ciclo(db)
    ciclo2 = CicloMonitoramentoService(
        coleta=ColetaFalsa(79, quando=BASE + timedelta(days=31))
    ).executar_ciclo(db)

    assert len(smtp_falso) == 1  # RN08/RN11
    assert ciclo2.produtos[0].alertas_ignorados == 1


def test_falha_na_analise_de_um_produto_nao_derruba_o_ciclo(db, produto, usuario, smtp_falso):
    outro = Produto(nome="Mouse", url_produto="https://loja.com.br/p/2", loja_id=produto.loja_id)
    db.add(outro)
    db.commit()

    class AnaliseQuebrada:
        def __init__(self):
            self.n = 0

        def classificar(self, historico):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("boom")
            from app.services.analise_service import AnaliseService
            return AnaliseService().classificar(historico)

    ciclo = CicloMonitoramentoService(coleta=ColetaFalsa(50), analise=AnaliseQuebrada()).executar_ciclo(db)

    assert len(ciclo.produtos) == 2
    assert sum(1 for i in ciclo.produtos if i.erro) == 1
    assert sum(1 for i in ciclo.produtos if i.analise) == 1


def test_produto_inativo_nao_entra_no_ciclo(db, produto):
    produto.ativo = False
    db.commit()
    assert CicloMonitoramentoService(coleta=ColetaFalsa(10)).executar_ciclo(db).produtos == []


def test_job_do_agendador_usa_o_ciclo_completo(monkeypatch):
    """O job do APScheduler deve chamar o ciclo (e não só a coleta)."""
    chamadas = []

    class CicloFalso:
        def executar_ciclo(self, db):
            chamadas.append(db)
            from app.services.ciclo_service import ResultadoCiclo
            return ResultadoCiclo()

    monkeypatch.setattr("app.services.ciclo_service.CicloMonitoramentoService", CicloFalso)
    executar_coleta_periodica()
    assert len(chamadas) == 1
