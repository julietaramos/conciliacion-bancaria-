import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, Date, JSON, LargeBinary, ForeignKey
from sqlalchemy import types
from sqlalchemy.orm import relationship
from db.database import Base


class GUID(types.TypeDecorator):
    impl = types.String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value else None

    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value else None


class Banco(Base):
    __tablename__ = "bancos"

    id         = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id    = Column(GUID, nullable=True, index=True)
    nombre     = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conciliaciones = relationship("Conciliacion", back_populates="banco", cascade="all, delete-orphan")


class Conciliacion(Base):
    __tablename__ = "conciliaciones"

    id             = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id        = Column(GUID, nullable=True, index=True)
    banco_id       = Column(GUID, ForeignKey("bancos.id"), nullable=True, index=True)
    fecha_proceso  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fecha_datos    = Column(Date, nullable=True)
    saldo_banco    = Column(Numeric(18, 2), nullable=True)
    saldo_contable = Column(Numeric(18, 2), nullable=True)
    diferencia     = Column(Numeric(18, 2), nullable=True)
    estado              = Column(String(30), default="completada")
    resumen             = Column(JSON, nullable=True)
    partidas_pendientes = Column(JSON, nullable=True)
    excel_output        = Column(LargeBinary, nullable=True)

    banco = relationship("Banco", back_populates="conciliaciones")
