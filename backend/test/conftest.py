import os
import uuid

# Variáveis fictícias ANTES de importar a app (database.py exige as três).
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SUPABASE_URL", "https://exemplo.supabase.co")
os.environ.setdefault(
    "SUPABASE_SECRET_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.assinatura",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import get_usuario_atual
from app.main import app
from app.models.usuario import Usuario


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine, autoflush=False)()
    yield sessao
    sessao.close()


def _criar_usuario(db, nome="Ana"):
    u = Usuario(id=uuid.uuid4(), nome=nome)
    db.add(u)
    db.commit()
    return u


@pytest.fixture()
def usuario(db):
    return _criar_usuario(db)


@pytest.fixture()
def outro_usuario(db):
    return _criar_usuario(db, "Bia")


@pytest.fixture()
def client(db, usuario):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    yield TestClient(app)
    app.dependency_overrides.clear()
