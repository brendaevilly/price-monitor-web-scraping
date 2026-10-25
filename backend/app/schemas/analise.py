import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from app.services.analise_service import ClassificacaoQueda


class AnaliseProdutoOut(BaseModel):
    """Resultado do UC11 (Comparar Preços e Identificar Queda) para um produto."""

    produto_id: uuid.UUID
    nome: str
    preco_atual: Decimal | None
    media_historica: Decimal | None = Field(
        description="Média das coletas anteriores válidas. None sem amostras suficientes (RN10)."
    )
    amostras_media: int = Field(description="Quantidade de coletas anteriores usadas na média.")
    amostras_minimas: int = Field(description="Mínimo de coletas anteriores exigido para classificar (RN10).")
    variacao_percentual_anterior: float | None = Field(
        description="Em relação à coleta anterior. Positivo = queda, negativo = alta."
    )
    variacao_percentual_media: float | None = Field(
        description="Em relação à média histórica. Positivo = queda, negativo = alta."
    )
    classificacao: ClassificacaoQueda
    queda_relevante: bool = Field(description="True nas faixas queda_relevante e grande_queda (>= 10%).")
