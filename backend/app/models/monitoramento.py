import uuid
from sqlalchemy import Column, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Monitoramento(Base):
    __tablename__ = "monitoramentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    preco_alvo = Column(Numeric(10, 2))
    alerta_ativo = Column(Boolean, default=True, nullable=False)
    data_cadastro = Column(DateTime(timezone=True), server_default=func.now())