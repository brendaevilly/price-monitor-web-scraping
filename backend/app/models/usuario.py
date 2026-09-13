import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True)  # referencia auth.users.id
    nome = Column(String, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())