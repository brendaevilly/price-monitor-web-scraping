import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ColetaPrecoOut(BaseModel):
    """Uma coleta válida de preço (RN09: inválidas já foram filtradas antes de chegar aqui)."""

    model_config = ConfigDict(from_attributes=True)

    preco: Decimal  # valor medido: produto + frete (issue #105)
    data_hora_coleta: datetime
    frete: Decimal | None = None  # parte de `preco` que é frete; 0 = grátis; None = não informado


class HistoricoProdutoOut(BaseModel):
    """Histórico de preços de um único produto (RN09: nunca mistura produtos diferentes)."""

    produto_id: uuid.UUID
    nome: str
    url_produto: str
    coletas: list[ColetaPrecoOut]  # ordem cronológica (mais antiga -> mais recente)
    preco_atual: Decimal | None  # produto + frete
    frete_atual: Decimal | None = None  # frete da coleta mais recente (0 = grátis; None = não informado)
    menor_preco: Decimal | None
    media_historica: Decimal | None  # None quando não há dados suficientes (RN10)
    amostras_media: int
