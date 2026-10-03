import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.models.usuario import Usuario

EMAIL = "ana@exemplo.com"
SENHA = "senha12345"


def _sessao_falsa(user_id):
    """Imita a resposta de sucesso do supabase.auth.sign_in_with_password."""
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        session=SimpleNamespace(
            access_token="token-de-acesso-falso",
            refresh_token="token-de-refresh-falso",
            expires_in=3600,
        ),
    )


def test_login_ok(client, db, usuario):
    with patch("app.routers.usuario.supabase") as supabase_mock:
        supabase_mock.auth.sign_in_with_password.return_value = _sessao_falsa(usuario.id)
        r = client.post("/usuarios/login", json={"email": EMAIL, "senha": SENHA})

    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["access_token"] == "token-de-acesso-falso"
    assert corpo["refresh_token"] == "token-de-refresh-falso"
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario"]["id"] == str(usuario.id)
    assert corpo["usuario"]["email"] == EMAIL
    supabase_mock.auth.sign_in_with_password.assert_called_once_with(
        {"email": EMAIL, "password": SENHA}
    )


def test_login_credenciais_invalidas(client, db, usuario):
    with patch("app.routers.usuario.supabase") as supabase_mock:
        supabase_mock.auth.sign_in_with_password.side_effect = Exception(
            "Invalid login credentials"
        )
        r = client.post("/usuarios/login", json={"email": EMAIL, "senha": "errada"})

    assert r.status_code == 401
    assert r.json()["detail"] == "E-mail ou senha incorretos."


def test_login_email_nao_confirmado(client, db, usuario):
    with patch("app.routers.usuario.supabase") as supabase_mock:
        supabase_mock.auth.sign_in_with_password.side_effect = Exception(
            "Email not confirmed"
        )
        r = client.post("/usuarios/login", json={"email": EMAIL, "senha": SENHA})

    assert r.status_code == 403
    assert "confirmado" in r.json()["detail"].lower()


def test_login_usuario_sem_cadastro_no_dominio(client, db):
    # Existe no Supabase Auth, mas não na tabela usuarios (inconsistência).
    with patch("app.routers.usuario.supabase") as supabase_mock:
        supabase_mock.auth.sign_in_with_password.return_value = _sessao_falsa(uuid.uuid4())
        r = client.post("/usuarios/login", json={"email": EMAIL, "senha": SENHA})

    assert r.status_code == 403
    assert "incompleto" in r.json()["detail"].lower()


def test_login_payload_invalido(client):
    assert client.post("/usuarios/login", json={"email": "nao-e-email", "senha": "x"}).status_code == 422
    assert client.post("/usuarios/login", json={"email": EMAIL}).status_code == 422
