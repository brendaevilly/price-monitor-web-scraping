import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class MonitoramentoCreate(BaseModel):
    """Vincula um produto já cadastrado à lista de monitoramento do usuário
    (UC04). O alerta nasce ativo (padrão do modelo); use PATCH para desativar."""

    produto_id: uuid.UUID
    preco_alvo: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Opcional. O alerta dispara quando o preço ficar menor ou igual a este valor (RF04, RN07).",
    )


class MonitoramentoUpdate(BaseModel):
    """Atualiza um monitoramento existente (UC08). Campos omitidos
    permanecem inalterados. Envie 'preco_alvo': null para remover o
    preço-alvo já definido; envie 'alerta_ativo': true/false para ativar
    ou desativar os alertas deste produto."""

    preco_alvo: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    alerta_ativo: bool | None = None

    @model_validator(mode="after")
    def _ao_menos_um_campo(self):
        if not self.model_fields_set:
            raise ValueError("Informe preco_alvo e/ou alerta_ativo para atualizar.")
        return self
