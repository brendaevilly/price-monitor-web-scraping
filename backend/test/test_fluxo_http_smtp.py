"""Encadeamento completo com os serviços REAIS e só as bordas simuladas (RNF12).

coleta (HTTP) -> HistoricoPreco -> AnaliseService -> AlertaService (SMTP)

Simulados: `requests.get` (loja), `smtplib.SMTP` (e-mail) e o Supabase Auth
(busca do e-mail do usuário). Nada sai para a rede e nada dorme: o intervalo
entre requisições é zerado e o "tempo" do reenvio é controlado pela data do
alerta já gravado.

Cobre: coleta válida gera histórico (RN09), a análise classifica a queda
(UC11, RN10), o alerta dispara uma vez e respeita o intervalo de reenvio
(RN08, RN11, UC13).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import requests

from app.config import settings
from app.models.alerta import Alerta
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.services.ciclo_service import CicloMonitoramentoService

BASE = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)  # bem no passado: a coleta nova é sempre a mais recente
URL = "https://loja.com.br/p/1"


# ---------- simulações das bordas ----------

def _pagina(preco):
    return (
        '<html><head><script type="application/ld+json">'
        f'{{"@type":"Product","name":"Notebook","offers":{{"price":"{preco}","priceCurrency":"BRL"}}}}'
        "</script></head><body></body></html>"
    )


class _Resposta:
    def __init__(self, texto, status=200):
        self.text, self.status_code = texto, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _Http:
    """Substitui requests.get: devolve (ou levanta) as respostas na ordem em que foram enfileiradas."""

    def __init__(self):
        self.respostas, self.chamadas = [], []

    def enfileirar(self, *respostas):
        self.respostas.extend(respostas)

    def __call__(self, url, **kwargs):
        self.chamadas.append(url)
        if not self.respostas:
            raise RuntimeError("requisição HTTP inesperada (nenhuma resposta enfileirada)")
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class _Smtp:
    """Substitui smtplib.SMTP e guarda o que seria enviado."""

    def __init__(self):
        self.conexoes, self.mensagens, self.falhar = [], [], False

    def __call__(self, host, port, timeout=None):
        smtp = self
        conexao = SimpleNamespace(host=host, port=port, tls=False, login=None)
        self.conexoes.append(conexao)

        class _Sessao:
            def __enter__(self_):
                return self_

            def __exit__(self_, *exc):
                return False

            def starttls(self_):
                conexao.tls = True

            def login(self_, usuario, senha):
                conexao.login = (usuario, senha)

            def send_message(self_, mensagem):
                if smtp.falhar:
                    raise OSError("SMTP fora do ar")
                smtp.mensagens.append(mensagem)

        return _Sessao()


@pytest.fixture()
def http(monkeypatch):
    falso = _Http()
    monkeypatch.setattr("app.services.coleta_service.requests.get", falso)
    return falso


@pytest.fixture()
def smtp(monkeypatch):
    falso = _Smtp()
    monkeypatch.setattr("app.services.alerta_service.smtplib.SMTP", falso)
    return falso


@pytest.fixture(autouse=True)
def ambiente(monkeypatch, usuario, outro_usuario):
    """Configuração de envio real (não dry-run), sem esperas, e Supabase Auth simulado."""
    for nome, valor in {
        "COLETA_INTERVALO_MINIMO_SEGUNDOS": 0.0,
        "COLETA_MAX_TENTATIVAS": 1,
        "ALERTA_SMTP_DRY_RUN": False,
        "ALERTA_INTERVALO_REENVIOS_HORAS": 24,
        "ALERTA_QUEDA_MINIMA_PERCENTUAL": 5.0,
        "SMTP_HOST": "smtp.teste",
        "SMTP_PORT": 587,
        "SMTP_USER": "robo",
        "SMTP_PASSWORD": "segredo",
        "SMTP_FROM": "alertas@pricebrother.test",
        "SMTP_USAR_TLS": True,
    }.items():
        monkeypatch.setattr(settings, nome, valor)

    emails = {usuario.id: "ana@example.com", outro_usuario.id: "bia@example.com"}

    def get_user_by_id(user_id):
        import uuid
        return SimpleNamespace(user=SimpleNamespace(email=emails[uuid.UUID(user_id)]))

    monkeypatch.setattr(
        "app.database.supabase",
        SimpleNamespace(auth=SimpleNamespace(admin=SimpleNamespace(get_user_by_id=get_user_by_id))),
    )


# ---------- cenário ----------

@pytest.fixture()
def produto(db):
    loja = Loja(nome="Loja", dominio="loja.com.br")
    db.add(loja)
    db.commit()
    p = Produto(nome="Notebook", url_produto=URL, loja_id=loja.id)
    db.add(p)
    db.commit()
    return p


def _historico(db, produto, precos):
    for i, preco in enumerate(precos):
        db.add(HistoricoPreco(
            produto_id=produto.id,
            preco=Decimal(str(preco)),
            data_hora_coleta=BASE + timedelta(days=i),
            coleta_valida=True,
        ))
    db.commit()


def _monitorar(db, usuario, produto, preco_alvo=None, alerta_ativo=True):
    db.add(Monitoramento(
        usuario_id=usuario.id, produto_id=produto.id,
        preco_alvo=preco_alvo, alerta_ativo=alerta_ativo,
    ))
    db.commit()


def _ciclo(db):
    return CicloMonitoramentoService().executar_ciclo(db)


def _envelhecer_alertas(db, horas):
    db.query(Alerta).update({"data_envio": datetime.now(timezone.utc) - timedelta(hours=horas)})
    db.commit()


# ---------- coleta válida -> histórico -> análise -> um e-mail ----------

def test_coleta_http_valida_gera_historico_classifica_e_envia_um_email(db, produto, usuario, http, smtp):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    http.enfileirar(_Resposta(_pagina("80.00")))

    ciclo = _ciclo(db)

    # coleta: uma requisição à URL do produto e uma nova linha válida no histórico
    assert http.chamadas == [URL]
    historico = db.query(HistoricoPreco).filter_by(produto_id=produto.id).order_by(HistoricoPreco.data_hora_coleta).all()
    assert len(historico) == 4
    assert historico[-1].preco == Decimal("80.00") and historico[-1].coleta_valida is True

    # análise: 20% abaixo da média 100 -> grande queda
    item = ciclo.produtos[0]
    assert item.analise.classificacao.value == "grande_queda"
    assert item.analise.media_historica == Decimal("100")

    # alerta: um registro e um e-mail, com os dados do UC13
    assert db.query(Alerta).count() == 1
    assert len(smtp.mensagens) == 1
    msg = smtp.mensagens[0]
    assert msg["To"] == "ana@example.com"
    assert msg["From"] == "alertas@pricebrother.test"
    assert "queda de preço" in msg["Subject"] and "Notebook" in msg["Subject"]
    corpo = msg.get_content()
    assert "20.00%" in corpo and "R$ 80.00" in corpo and URL in corpo
    # conexão SMTP configurada como pedido: TLS e login
    assert smtp.conexoes[0].host == "smtp.teste" and smtp.conexoes[0].port == 587
    assert smtp.conexoes[0].tls is True
    assert smtp.conexoes[0].login == ("robo", "segredo")
    assert (ciclo.validas, ciclo.analisados, ciclo.alertas_enviados) == (1, 1, 1)


def test_retry_http_depois_de_timeout_ainda_gera_coleta_valida(db, produto, usuario, http, smtp, monkeypatch):
    monkeypatch.setattr(settings, "COLETA_MAX_TENTATIVAS", 3)
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    http.enfileirar(requests.Timeout("lento"), _Resposta("", 503), _Resposta(_pagina("80.00")))

    ciclo = _ciclo(db)

    assert len(http.chamadas) == 3
    assert ciclo.produtos[0].coleta.coleta_valida is True
    assert ciclo.produtos[0].coleta.tentativas == 3
    assert len(smtp.mensagens) == 1


def test_preco_alvo_atingido_envia_email_de_preco_alvo(db, produto, usuario, http, smtp):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, preco_alvo=Decimal("99"))
    http.enfileirar(_Resposta(_pagina("98.00")))  # só 2% de queda: apenas o alvo dispara

    _ciclo(db)

    assert [m["Subject"] for m in smtp.mensagens] == ["PriceBrother: preço-alvo atingido em Notebook"]


def test_alerta_desativado_pelo_usuario_nao_envia(db, produto, usuario, http, smtp):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, alerta_ativo=False)
    http.enfileirar(_Resposta(_pagina("50.00")))

    ciclo = _ciclo(db)

    assert ciclo.produtos[0].analise is not None  # a análise acontece
    assert smtp.mensagens == [] and db.query(Alerta).count() == 0


def test_cada_usuario_que_monitora_recebe_um_email(db, produto, usuario, outro_usuario, http, smtp):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    _monitorar(db, outro_usuario, produto)
    http.enfileirar(_Resposta(_pagina("80.00")), _Resposta(_pagina("79.00")))

    _ciclo(db)
    _ciclo(db)  # segundo ciclo, dentro do intervalo: ninguém recebe de novo

    assert sorted(m["To"] for m in smtp.mensagens) == ["ana@example.com", "bia@example.com"]
    assert db.query(Alerta).count() == 2


# ---------- RN09: coleta inválida não analisa nem alerta ----------

@pytest.mark.parametrize("resposta", [
    _Resposta("", 500),                                      # erro HTTP
    requests.Timeout("lento"),                               # timeout
    _Resposta("<html><body>sem preço</body></html>"),        # página sem preço
    _Resposta("<html>suspicious-traffic</html>"),            # loja bloqueou o robô
], ids=["http_500", "timeout", "sem_preco", "bloqueado"])
def test_coleta_http_invalida_nao_analisa_nem_alerta_e_preserva_historico(db, produto, usuario, http, smtp, resposta):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto, preco_alvo=Decimal("90"))
    http.enfileirar(resposta)

    ciclo = _ciclo(db)

    item = ciclo.produtos[0]
    assert item.coleta.coleta_valida is False
    assert item.analise is None and item.alertas == []
    assert smtp.mensagens == [] and db.query(Alerta).count() == 0
    # histórico anterior intacto (3 válidas) + 1 linha marcada como inválida
    validas = db.query(HistoricoPreco).filter_by(produto_id=produto.id, coleta_valida=True).count()
    invalidas = db.query(HistoricoPreco).filter_by(produto_id=produto.id, coleta_valida=False).count()
    assert (validas, invalidas) == (3, 1)


# ---------- RN08 / RN11: intervalo de reenvio ----------

@pytest.mark.parametrize("horas_desde_o_primeiro, emails_esperados", [
    (0, 1),    # logo em seguida: ignorado
    (23, 1),   # ainda dentro das 24 h: ignorado
    (25, 2),   # passou do intervalo: envia de novo
])
def test_reenvio_respeita_o_intervalo(db, produto, usuario, http, smtp, horas_desde_o_primeiro, emails_esperados):
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    http.enfileirar(_Resposta(_pagina("80.00")), _Resposta(_pagina("79.00")))

    primeiro = _ciclo(db)
    assert len(smtp.mensagens) == 1 and primeiro.alertas_enviados == 1

    if horas_desde_o_primeiro:
        _envelhecer_alertas(db, horas_desde_o_primeiro)
    segundo = _ciclo(db)

    assert len(smtp.mensagens) == emails_esperados
    assert db.query(Alerta).count() == emails_esperados
    assert segundo.produtos[0].alertas_ignorados == (1 if emails_esperados == 1 else 0)


def test_intervalo_de_reenvio_vem_da_configuracao(db, produto, usuario, http, smtp, monkeypatch):
    monkeypatch.setattr(settings, "ALERTA_INTERVALO_REENVIOS_HORAS", 48)
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    http.enfileirar(_Resposta(_pagina("80.00")), _Resposta(_pagina("79.00")))

    _ciclo(db)
    _envelhecer_alertas(db, 25)  # passaria com 24 h, mas o intervalo agora é 48 h
    _ciclo(db)

    assert len(smtp.mensagens) == 1


def test_falha_no_smtp_nao_consome_o_intervalo(db, produto, usuario, http, smtp):
    """Se o e-mail não saiu, nada é gravado como enviado e o ciclo seguinte tenta de novo."""
    _historico(db, produto, [100, 100, 100])
    _monitorar(db, usuario, produto)
    http.enfileirar(_Resposta(_pagina("80.00")), _Resposta(_pagina("79.00")))

    smtp.falhar = True
    primeiro = _ciclo(db)
    assert primeiro.alertas_enviados == 0 and primeiro.produtos[0].erro is None
    assert db.query(Alerta).count() == 0

    smtp.falhar = False
    _ciclo(db)
    assert len(smtp.mensagens) == 1 and db.query(Alerta).count() == 1