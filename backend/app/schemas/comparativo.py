import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.loja import LojaOut


class OfertaLojaOut(BaseModel):
    """O mesmo produto numa loja: a última coleta válida (preço já com frete, issue #105)."""

    produto_id: uuid.UUID
    loja: LojaOut
    url_produto: str
    preco_atual: Decimal | None  # None = ainda sem coleta válida (RN09)
    frete: Decimal | None = None  # 0 = grátis; None = não informado
    data_hora_coleta: datetime | None = None
    menor_preco: Decimal | None = None  # menor preço válido já visto nesta loja
    melhor_oferta: bool = False


class ComparativoLojasOut(BaseModel):
    """Comparativo do produto entre as lojas que o usuário monitora (issue #104)."""

    produto_id: uuid.UUID
    nome: str
    grupo_id: uuid.UUID | None
    ofertas: list[OfertaLojaOut]  # da mais barata para a mais cara; sem preço por último
    melhor_oferta_produto_id: uuid.UUID | None  # None se nenhuma loja tem preço ainda
    economia: Decimal | None  # mais cara - mais barata (só com 2+ lojas com preço)
