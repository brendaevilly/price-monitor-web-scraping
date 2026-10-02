
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import historico_preco, loja, produto, usuario  # noqa: F401
from app.routers import usuario as usuario_router
from app.scheduler import iniciar_agendador, parar_agendador, status_agendador

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    iniciar_agendador()
    yield
    parar_agendador()


app = FastAPI(
    title="PriceBrother API",
    description="Plataforma de monitoramento de preços via web scraping.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "coleta_periodica": status_agendador()}


app.include_router(usuario_router.router)
