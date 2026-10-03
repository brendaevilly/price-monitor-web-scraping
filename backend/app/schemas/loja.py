import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.urls import URLInvalida, normalizar_dominio


class LojaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    dominio: str = Field(
        description="Domínio da loja (ex.: 'kabum.com.br'). Também aceita a URL da loja.",
        examples=["kabum.com.br"],
    )

    @field_validator("nome")
    @classmethod
    def _limpar_nome(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("O nome da loja deve ter ao menos 2 caracteres.")
        return v

    @field_validator("dominio")
    @classmethod
    def _validar_dominio(cls, v: str) -> str:
        try:
            return normalizar_dominio(v)
        except URLInvalida as exc:
            raise ValueError(str(exc))


class LojaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    dominio: str
