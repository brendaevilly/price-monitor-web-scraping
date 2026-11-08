"""Mensagens de erro, logs e isolamento entre usuários (RNF03).

Cobre o que foi levantado após a apresentação de 26/10:
  * erros de validação, autenticação, coleta e envio em português e sem
    detalhes técnicos;
  * logs que identificam a falha (autenticação, coleta, persistência, envio)
    sem registrar senha nem token;
  * um usuário nunca lê nem altera dados de outro.
"""
import io
import logging
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.database import get_db
from app.dependencies import get_usuario_atual
from app.logging_config import FiltroSegredos, redigir
from app.main import app
from app.models.alerta import Alerta
from app.models.historico_preco import HistoricoPreco
from app.models.loja import Loja
from app.models.monitoramento import Monitoramento
from app.models.produto import Produto
from app.services.alerta_service import Analise, AlertaService
from app.services.coleta_service import MOTIVO_BANCO, ColetaService

SENHA = "SenhaSecreta123"
TERMOS_TECNICOS = (
    "Traceback", "Exception", "psycopg2", "sqlalchemy", "supabase", "Supabase",
    "HTTPSConnectionPool", "Internal Server Error", "Field required", "OperationalError",
)


def _sem_termos_tecnicos(texto: str):
    for termo in TERMOS_TECNICOS:
        assert termo not in texto, f"vazou detalhe técnico: {termo!r} em {texto!r}"


@pytest.fixture()
def publico(db):
    """Cliente sem override de autenticação (rotas públicas e testes do token)."""
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def como(db):
    """como(usuario) -> cliente autenticado como esse usuário."""
    app.dependency_overrides[get_db] = lambda: db

    def _cliente(u):
        app.dependency_overrides[get_usuario_atual] = lambda: u
        return TestClient(app, raise_server_exceptions=False)

    yield _cliente
    app.dependency_overrides.clear()


# ----------------------------------------------------------------- validação
def test_422_em_portugues_e_sem_eco_da_senha(publico):
    r = publico.post("/usuarios", json={"email": "a@b.com", "senha": SENHA})
    assert r.status_code == 422
    assert SENHA not in r.text                      # o `input` padrão devolvia o corpo inteiro
    assert '"input"' not in r.text
    assert "campo obrigatório" in r.json()["detail"]
    _sem_termos_tecnicos(r.text)


def test_422_login_sem_senha_nao_ecoa_corpo(publico):
    r = publico.post("/usuarios/login", json={"email": "a@b.com"})
    assert r.status_code == 422
    assert "a@b.com" not in r.text
    assert "senha" in r.json()["detail"]


def test_422_senha_curta_e_email_invalido(publico):
    r = publico.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": "curta"})
    assert "ao menos 8 caracteres" in r.json()["detail"]
    assert "curta" not in r.json()["detail"].replace("curta demais", "")
    r = publico.post("/usuarios", json={"nome": "Ana", "email": "nao-e-email", "senha": SENHA})
    assert "e-mail inválido" in r.json()["detail"]
    assert SENHA not in r.text


def test_422_json_malformado(publico):
    r = publico.post("/usuarios/login", content="{quebrado", headers={"content-type": "application/json"})
    assert r.status_code == 422
    assert "não é um JSON válido" in r.json()["detail"]


def test_404_de_rota_inexistente_em_portugues(publico):
    r = publico.get("/rota-que-nao-existe")
    assert r.status_code == 404 and r.json()["detail"] == "Recurso não encontrado."
    r = publico.delete("/usuarios")
    assert r.status_code == 405 and "não permitido" in r.json()["detail"]


def test_500_generico_em_portugues_sem_vazar_causa(como, db, usuario, caplog):
    loja = Loja(nome="L", dominio="loja.com.br"); db.add(loja); db.commit()
    p = Produto(nome="Fone", url_produto="https://loja.com.br/fone", loja_id=loja.id)
    db.add(p); db.commit()
    db.add(Monitoramento(usuario_id=usuario.id, produto_id=p.id)); db.commit()
    segredo = "password authentication failed for user postgres host=db.abc.supabase.co"
    with patch("app.routers.produto._coletas_validas", side_effect=RuntimeError(segredo)):
        r = como(usuario).get(f"/produtos/{p.id}/historico")
    assert r.status_code == 500
    assert r.json() == {"detail": "Ocorreu um erro interno. Tente novamente em instantes."}
    assert "supabase" not in r.text.lower()
    assert any("Erro não tratado" in rec.getMessage() for rec in caplog.records)  # fica no log


# --------------------------------------------------------------- autenticação
def test_cadastro_com_auth_fora_do_ar_nao_vaza_detalhe(publico):
    sb = MagicMock()
    sb.auth.admin.create_user.side_effect = httpx.ConnectError(
        "HTTPSConnectionPool(host='xyz.supabase.co', port=443)"
    )
    with patch("app.routers.usuario.supabase", sb):
        r = publico.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": SENHA})
    assert r.status_code == 503
    _sem_termos_tecnicos(r.text)
    assert "xyz" not in r.text and SENHA not in r.text
    assert "Tente novamente" in r.json()["detail"]


def test_cadastro_com_erro_inesperado_do_auth_nao_vaza_detalhe(publico):
    sb = MagicMock()
    sb.auth.admin.create_user.side_effect = Exception("boom key=eyJabcdefghijk.abcdef.xyz")
    with patch("app.routers.usuario.supabase", sb):
        r = publico.post("/usuarios", json={"nome": "Ana", "email": "a@b.com", "senha": SENHA})
    assert r.status_code == 502
    _sem_termos_tecnicos(r.text)
    assert "eyJ" not in r.text


def test_login_com_auth_fora_do_ar_nao_diz_que_a_senha_esta_errada(publico):
    sb = MagicMock()
    sb.auth.sign_in_with_password.side_effect = httpx.ConnectError("sem rede")
    with patch("app.routers.usuario.supabase", sb):
        r = publico.post("/usuarios/login", json={"email": "a@b.com", "senha": SENHA})
    assert r.status_code == 503
    assert "incorretos" not in r.json()["detail"]


def test_login_com_senha_errada_registra_falha_sem_senha(publico, caplog):
    caplog.set_level(logging.INFO)
    sb = MagicMock()
    sb.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    sb.auth.admin.list_users.return_value = MagicMock(users=[])
    with patch("app.routers.usuario.supabase", sb):
        r = publico.post("/usuarios/login", json={"email": "ana@gmail.com", "senha": SENHA})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha incorretos."
    texto = caplog.text
    assert "Falha de autenticação no login" in texto
    assert SENHA not in texto
    assert "ana@gmail.com" not in texto          # e-mail só mascarado
    assert "an***@gmail.com" in texto


def test_requisicao_sem_token_e_registrada(publico, caplog):
    caplog.set_level(logging.INFO)
    r = publico.get("/produtos")
    assert r.status_code == 401 and "Faça login" in r.json()["detail"]
    assert "requisição sem token" in caplog.text


def test_token_invalido_e_registrado_sem_o_token(publico, caplog):
    caplog.set_level(logging.INFO)
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.assinaturaSecreta"
    sb = MagicMock(); sb.auth.get_user.side_effect = Exception("invalid JWT")
    with patch("app.dependencies.supabase", sb):
        r = publico.get("/produtos", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and "Sessão inválida" in r.json()["detail"]
    assert "Falha de autenticação" in caplog.text
    assert token not in caplog.text and "assinaturaSecreta" not in caplog.text


def test_auth_indisponivel_na_validacao_do_token_devolve_503_e_nao_401(publico, caplog):
    sb = MagicMock(); sb.auth.get_user.side_effect = httpx.ConnectError("sem rede")
    with patch("app.dependencies.supabase", sb):
        r = publico.get("/produtos", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 503
    assert "indisponível" in r.json()["detail"]
    assert "indisponível" in caplog.text


# -------------------------------------------------------------------- coleta
def _produto_books(db):
    loja = Loja(nome="L", dominio="books.toscrape.com"); db.add(loja); db.commit()
    p = Produto(nome="Livro", url_produto="https://books.toscrape.com/x", loja_id=loja.id)
    db.add(p); db.commit()
    return p


class _Resposta:
    text = '<p class="price_color">£10.00</p>'
    def raise_for_status(self): pass


def test_falha_de_banco_na_coleta_nao_levanta_e_nao_vaza_detalhe(db, caplog):
    """Antes: reler o produto expirado após o rollback lançava exceção para fora."""
    caplog.set_level(logging.INFO)
    p = _produto_books(db)
    caiu = {"v": False}
    execute_original = db.execute

    def commit_quebrado():
        caiu["v"] = True
        raise OperationalError(
            "INSERT", {}, Exception('connection to server at "db.abc.supabase.co" failed')
        )

    def execute_quebrado(*a, **k):
        if caiu["v"]:
            raise OperationalError("SELECT", {}, Exception("server closed the connection"))
        return execute_original(*a, **k)

    with patch.object(ColetaService, "_requisitar", return_value=_Resposta()), \
         patch.object(db, "commit", commit_quebrado), \
         patch.object(db, "execute", execute_quebrado):
        r = ColetaService().executar_coleta(p, db)

    assert r.sucesso is False and r.coleta_valida is False and r.motivo_falha == MOTIVO_BANCO
    assert r.preco is None
    assert "supabase" not in (r.erro or "").lower() and "db.abc" not in (r.erro or "")
    assert "não foi possível gravar" in caplog.text           # falha de persistência visível no log


def test_falha_de_coleta_gera_linha_invalida_e_log_com_motivo(db, caplog):
    caplog.set_level(logging.INFO)
    p = _produto_books(db)
    with patch.object(ColetaService, "_requisitar", side_effect=httpx.ConnectError("x")):
        # requests.RequestException é o que a coleta classifica como rede
        import requests
        with patch.object(ColetaService, "_requisitar", side_effect=requests.ConnectionError("sem rede")):
            r = ColetaService().executar_coleta(p, db)
    assert r.motivo_falha == "rede" and r.preco is None
    linha = db.query(HistoricoPreco).filter_by(produto_id=p.id).one()
    assert linha.coleta_valida is False and linha.preco is None   # nunca 0.00
    assert "[rede]" in caplog.text and "Histórico anterior preservado" in caplog.text


# -------------------------------------------------------------------- alerta
def _dois_monitorando(db, usuario, outro_usuario):
    loja = Loja(nome="L", dominio="loja.com.br"); db.add(loja); db.commit()
    p = Produto(nome="Fone", url_produto="https://loja.com.br/fone", loja_id=loja.id)
    db.add(p); db.commit()
    for u in (usuario, outro_usuario):
        db.add(Monitoramento(usuario_id=u.id, produto_id=p.id))
    db.commit()
    return p


def test_falha_ao_gravar_alerta_ja_enviado_nao_interrompe_os_demais(db, usuario, outro_usuario, caplog):
    caplog.set_level(logging.INFO)
    p = _dois_monitorando(db, usuario, outro_usuario)
    analise = Analise(preco_atual=Decimal("80"), queda_percentual=Decimal("20"), houve_queda_relevante=True)
    commit_original = db.commit
    chamadas = {"n": 0}

    def commit_falha_na_primeira():
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise OperationalError("INSERT", {}, Exception("conexão perdida"))
        return commit_original()

    svc = AlertaService()
    with patch.object(svc, "_obter_email", return_value="x@y.com"), \
         patch.object(svc, "enviar_email"), patch.object(db, "commit", commit_falha_na_primeira):
        resultado = svc.avaliar_condicoes(p, analise, db)

    assert len(resultado.alertas) == 1                       # o segundo usuário ainda foi atendido
    assert "Falha de persistência" in caplog.text and "foi enviado" in caplog.text


def test_falha_de_smtp_e_registrada_com_produto_e_usuario(db, usuario, outro_usuario, caplog):
    caplog.set_level(logging.INFO)
    p = _dois_monitorando(db, usuario, outro_usuario)
    analise = Analise(preco_atual=Decimal("80"), queda_percentual=Decimal("20"), houve_queda_relevante=True)
    svc = AlertaService()
    with patch.object(svc, "_obter_email", return_value="x@y.com"), \
         patch.object(svc, "enviar_email", side_effect=OSError("smtp caiu")):
        resultado = svc.avaliar_condicoes(p, analise, db)
    assert resultado.alertas == []                            # nada gravado se o e-mail não saiu
    assert "Falha no envio do e-mail de alerta" in caplog.text
    assert str(usuario.id) in caplog.text and str(p.id) in caplog.text


def test_dry_run_nao_loga_corpo_nem_email_completo(caplog):
    caplog.set_level(logging.INFO)
    prod = Produto(id=uuid.uuid4(), nome="Fone", url_produto="https://loja.com.br/fone")
    alerta = Alerta(tipo="queda_preco", mensagem="Queda de 20%")
    with patch("app.services.alerta_service.settings") as cfg:
        cfg.ALERTA_SMTP_DRY_RUN = True; cfg.SMTP_FROM = "a@b.com"; cfg.SMTP_USER = ""
        AlertaService().enviar_email(alerta, "maria.souza@gmail.com", prod, "Maria")
    assert "maria.souza@gmail.com" not in caplog.text
    assert "Olá, Maria" not in caplog.text


# ------------------------------------------------------------ redação de logs
@pytest.mark.parametrize(
    "bruto, proibido",
    [
        ('{"email": "a@b.com", "senha": "SenhaSecreta123"}', "SenhaSecreta123"),
        ("login com senha=SenhaSecreta123 falhou", "SenhaSecreta123"),
        ("Authorization: Bearer abc.def.ghi-123", "abc.def.ghi-123"),
        ("token recusado eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiYSJ9.assin", "eyJhbGciOiJIUzI1NiJ9"),
        ("access_token: xyz123456", "xyz123456"),
        ("postgresql://postgres:MinhaSenhaDoBanco@db.abc.supabase.co:5432/postgres", "MinhaSenhaDoBanco"),
        ("SMTP_PASSWORD=segredo-smtp", "segredo-smtp"),
    ],
)
def test_redigir_remove_segredos(bruto, proibido):
    assert proibido not in redigir(bruto)


def test_redigir_preserva_mensagens_normais():
    for msg in (
        "E-mail ou senha incorretos.",
        "Falha de autenticação no login: credenciais recusadas (an***@gmail.com).",
        "password authentication failed for user postgres",
    ):
        assert redigir(msg) == msg


def test_handler_do_app_redige_mensagem_e_traceback():
    raiz = logging.getLogger()
    handler = next(h for h in raiz.handlers if getattr(h, "_pricebrother", False))
    original, handler.stream = handler.stream, io.StringIO()
    try:
        lg = logging.getLogger("app.teste")
        try:
            raise RuntimeError("falhou com password=SenhaSecreta123 e Bearer abc.def.ghi")
        except RuntimeError:
            lg.exception("erro ao autenticar senha=%s", "SenhaSecreta123")
        saida = handler.stream.getvalue()
    finally:
        handler.stream = original
    assert "erro ao autenticar" in saida and "Traceback" in saida     # continua útil
    assert "SenhaSecreta123" not in saida and "abc.def.ghi" not in saida


# ---------------------------------------------------------------------- CORS
def test_cors_libera_origem_do_frontend(publico):
    r = publico.options(
        "/usuarios/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    r = publico.options("/usuarios/login", headers={"Origin": "https://site-malicioso.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


# --------------------------------------------------------------------- RNF03
@pytest.fixture()
def cenario(db, usuario, outro_usuario):
    """A (usuario) monitora um produto com histórico e recebeu um alerta; B não tem nada."""
    loja = Loja(nome="L", dominio="loja.com.br"); db.add(loja); db.commit()
    p = Produto(nome="Produto da Ana", url_produto="https://loja.com.br/ana", loja_id=loja.id)
    db.add(p); db.commit()
    mon = Monitoramento(usuario_id=usuario.id, produto_id=p.id, preco_alvo=Decimal("50"))
    db.add(mon)
    for v in ("100", "100", "100", "80"):
        db.add(HistoricoPreco(produto_id=p.id, preco=Decimal(v), coleta_valida=True))
    db.add(Alerta(produto_id=p.id, usuario_id=usuario.id, tipo="queda_preco", mensagem="Queda de 20%"))
    db.commit()
    return {"produto": p, "mon": mon}


def test_rnf03_usuario_b_nao_ve_nada_do_usuario_a(como, outro_usuario, cenario):
    b = como(outro_usuario)
    assert b.get("/produtos").json() == []
    assert b.get("/alertas").json() == []
    resumo = b.get("/analise/resumo").json()
    assert resumo["total_produtos"] == 0 and resumo["produtos"] == []


@pytest.mark.parametrize("sufixo", ["historico", "analise"])
def test_rnf03_b_nao_acessa_historico_nem_analise_de_a(como, outro_usuario, cenario, sufixo):
    pid = cenario["produto"].id
    r = como(outro_usuario).get(f"/produtos/{pid}/{sufixo}")
    inexistente = como(outro_usuario).get(f"/produtos/{uuid.uuid4()}/{sufixo}")
    assert r.status_code == 404
    assert r.json() == inexistente.json()           # não revela que o produto existe


def test_rnf03_b_nao_altera_nem_remove_monitoramento_de_a(como, db, outro_usuario, cenario):
    mid = cenario["mon"].id
    b = como(outro_usuario)
    r1 = b.patch(f"/monitoramentos/{mid}", json={"alerta_ativo": False, "preco_alvo": "1.00"})
    r2 = b.delete(f"/monitoramentos/{mid}")
    assert r1.status_code == 404 and r2.status_code == 404
    assert r1.json() == b.patch(f"/monitoramentos/{uuid.uuid4()}", json={"alerta_ativo": False}).json()
    db.expire_all()
    mon = db.get(Monitoramento, mid)
    assert mon is not None and mon.alerta_ativo is True and mon.preco_alvo == Decimal("50.00")


def test_rnf03_a_continua_vendo_os_proprios_dados(como, usuario, cenario):
    a = como(usuario)
    assert len(a.get("/produtos").json()) == 1
    assert len(a.get("/alertas").json()) == 1
    assert a.get(f"/produtos/{cenario['produto'].id}/historico").status_code == 200


def test_rnf03_rotas_protegidas_exigem_autenticacao(publico, cenario):
    pid, mid = cenario["produto"].id, cenario["mon"].id
    for metodo, rota in [
        ("get", "/produtos"), ("get", f"/produtos/{pid}/historico"), ("get", f"/produtos/{pid}/analise"),
        ("get", "/alertas"), ("get", "/analise/resumo"), ("get", "/lojas"),
        ("patch", f"/monitoramentos/{mid}"), ("delete", f"/monitoramentos/{mid}"),
        ("post", "/monitoramentos"), ("post", "/produtos"), ("post", "/lojas"),
    ]:
        r = getattr(publico, metodo)(rota)
        assert r.status_code == 401, f"{metodo.upper()} {rota} respondeu {r.status_code} sem token"
