import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ColetaPrecoOut(BaseModel):
    """Uma coleta válida de preço (RN09: inválidas já foram filtradas antes de chegar aqui)."""

    model_config = ConfigDict(from_attributes=True)

    preco: Decimal
    data_hora_coleta: datetime


class HistoricoProdutoOut(BaseModel):
    """Histórico de preços de um único produto (RN09: nunca mistura produtos diferentes)."""

    produto_id: uuid.UUID
    nome: str
    url_produto: str
    coletas: list[ColetaPrecoOut]  # ordem cronológica (mais antiga -> mais recente)
    preco_atual: Decimal | None
    menor_preco: Decimal | None
    media_historica: Decimal | None  # None quando não há dados suficientes (RN10)
    amostras_media: int
