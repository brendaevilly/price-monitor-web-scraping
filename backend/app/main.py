from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import alerta, historico_preco, loja, monitoramento, produto, usuario  # noqa: F401
from app.routers import usuario as usuario_router
from app.scheduler import iniciar_agendador, parar_agendador, status_agendador
from app.routers import loja as loja_router
from app.routers import produto as produto_router
from app.routers import monitoramento as monitoramento_router

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
app.include_router(loja_router.router)
app.include_router(produto_router.router)
app.include_router(monitoramento_router.router)