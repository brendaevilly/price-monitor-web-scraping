import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProdutoResumoOut(BaseModel):
    """Produto ao qual o alerta se refere. O `id` serve para o frontend abrir
    o histórico (GET /produtos/{id}/historico), como pede o UC14."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    url_produto: str


class AlertaOut(BaseModel):
    id: uuid.UUID
    tipo: str  # "queda_preco" ou "preco_alvo"
    data_envio: datetime
    mensagem: str
    produto: ProdutoResumoOut