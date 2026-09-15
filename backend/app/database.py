
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from supabase import create_client, Client

from app.config import settings

# --- Conexão direta ao Postgres (SQLAlchemy) - usada para nossas tabelas de domínio ---
if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. Defina a variável de ambiente no arquivo .env "
        "com a connection string do Postgres do Supabase."
    )

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Cliente do Supabase Auth - usado para cadastro/login (auth.users) ---
if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_SECRET_KEY não configuradas. Defina-as no .env "
        "(Project Settings > API no painel do Supabase)."
    )

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)