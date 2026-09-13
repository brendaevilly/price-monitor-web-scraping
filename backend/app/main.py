from fastapi import FastAPI

app = FastAPI(
    title="PriceBrother API",
    description="Plataforma de monitoramento de preços via web scraping.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


