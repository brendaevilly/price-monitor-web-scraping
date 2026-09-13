import uuid
from sqlalchemy import Column, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class HistoricoPreco(Base):
    __tablename__ = "historico_precos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    data_hora_coleta = Column(DateTime(timezone=True), server_default=func.now())
    coleta_valida = Column(Boolean, default=True, nullable=False)