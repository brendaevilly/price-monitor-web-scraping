import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    email: EmailStr
    criado_em: datetime


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class LoginOut(BaseModel):
    """Token de acesso do Supabase Auth, para o frontend guardar e enviar
    como 'Authorization: Bearer <access_token>' nas próximas requisições."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: UsuarioOut