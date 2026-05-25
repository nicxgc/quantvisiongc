"""Modelo ORM para la entidad Estrategia."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import tipo_estrategia_enum

if TYPE_CHECKING:
    from app.models.contratacion import Contratacion
    from app.models.metrica_estrategia import MetricaEstrategia
    from app.models.resultado_estrategia import ResultadoEstrategia


class EstadoEstrategia(str, enum.Enum):
    ACTIVA = "activa"
    PAUSADA = "pausada"


class Estrategia(Base):
    """Tabla principal de estrategias de inversión."""

    __tablename__ = "estrategia"

    __table_args__ = (
        CheckConstraint(
            "nivel_riesgo >= 1 AND nivel_riesgo <= 7",
            name="ck_estrategia_nivel_riesgo",
        ),
    )

    # ---------------------------------------------------------------------------
    # BLOQUE 1: Datos descriptivos
    # ---------------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categoria: Mapped[str] = mapped_column(String(50), index=True)
    tipo_activo: Mapped[str] = mapped_column(String(50), index=True)
    nivel_riesgo: Mapped[int] = mapped_column()
    precio_subscripcion: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    comision_ganancias: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    estado: Mapped[EstadoEstrategia] = mapped_column(
        Enum(EstadoEstrategia, name="estado_estrategia",
             values_callable=lambda x: [e.value for e in x]),
        default=EstadoEstrategia.ACTIVA,
        index=True,
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    fecha_ult_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    # Soft delete: False oculta la estrategia sin borrar la fila ni sus históricos.
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---------------------------------------------------------------------------
    # BLOQUE 2: Identificación y clasificación (nuevo en T1.1)
    # ---------------------------------------------------------------------------
    # Código único legible por humanos (ej. "SP500_OOS_2024").
    codigo_estrategia: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Tipo de estrategia: 'estrategia_activa' o 'benchmark'.
    tipo: Mapped[str] = mapped_column(tipo_estrategia_enum, nullable=False)
    # Fecha de cierre de la estrategia; NULL si sigue activa.
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ---------------------------------------------------------------------------
    # Relaciones
    # ---------------------------------------------------------------------------
    resultados: Mapped[list["ResultadoEstrategia"]] = relationship(
        "ResultadoEstrategia",
        back_populates="estrategia",
        cascade="all, delete-orphan",
    )
    metricas: Mapped[list["MetricaEstrategia"]] = relationship(
        "MetricaEstrategia",
        back_populates="estrategia",
        cascade="all, delete-orphan",
    )
    contrataciones: Mapped[list["Contratacion"]] = relationship(
        "Contratacion",
        back_populates="estrategia",
    )
