import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.loja import LojaOut
from app.utils.urls import URLInvalida, normalizar_url_produto


class ProdutoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    url_produto: str = Field(examples=["https://www.kabum.com.br/produto/123456/mouse-gamer"])
    loja_id: uuid.UUID
    preco_alvo: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2,
        description="Opcional. O alerta dispara quando o preço ficar menor ou igual a este valor.",
    )

    @field_validator("nome")
    @classmethod
    def _limpar_nome(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("O nome do produto deve ter ao menos 2 caracteres.")
        return v

    @field_validator("url_produto")
    @classmethod
    def _validar_url(cls, v: str) -> str:
        try:
            return normalizar_url_produto(v)
        except URLInvalida as exc:
            raise ValueError(str(exc))


class ProdutoMonitoradoOut(BaseModel):
    """Produto visto pela ótica do usuário (Produto + Monitoramento)."""

    produto_id: uuid.UUID
    nome: str
    url_produto: str
    ativo: bool
    loja: LojaOut
    monitoramento_id: uuid.UUID
    preco_alvo: Decimal | None
    alerta_ativo: bool
    data_cadastro: datetime
