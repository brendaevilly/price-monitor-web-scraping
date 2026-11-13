import uuid
from sqlalchemy import Column, Numeric, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class HistoricoPreco(Base):
    __tablename__ = "historico_precos"
    # RNF01: histórico, análise e coleta filtram por produto e ordenam por
    # data/hora; este índice atende as duas coisas sem sort. O nome é o mesmo do
    # schema.sql e da migracao_002 para não duplicar o índice no banco.
    __table_args__ = (Index("idx_historico_produto", "produto_id", "data_hora_coleta"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id = Column(UUID(as_uuid=True), ForeignKey("produtos.id"), nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    data_hora_coleta = Column(DateTime(timezone=True), server_default=func.now())
    coleta_valida = Column(Boolean, default=True, nullable=False)
    # Issue #105: `preco` = produto + frete. Aqui fica só o frete (0 = grátis;
    # NULL = a página não informou).
    frete = Column(Numeric(10, 2), nullable=True)