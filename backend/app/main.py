
from fastapi import FastAPI

from app.database import Base, engine
from app.models import usuario  # noqa: F401 - garante que o modelo seja registrado no Base
from app.routers import usuario as usuario_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PriceBrother API",
    description="Plataforma de monitoramento de preços via web scraping.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app.include_router(usuario_router.router)