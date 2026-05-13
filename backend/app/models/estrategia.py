"""Modelo ORM para la entidad Estrategia. Combina las Tablas 3.28, 3.29 y 3.30 de la memoria."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contratacion import Contratacion
    from app.models.resultado_estrategia import ResultadoEstrategia


class EstadoEstrategia(str, enum.Enum):
    ACTIVA = "activa"
    PAUSADA = "pausada"


class Estrategia(Base):
    """Corresponde a las Tablas 3.28, 3.29 y 3.30 de la memoria."""

    __tablename__ = "estrategia"

    __table_args__ = (
        CheckConstraint(
            "nivel_riesgo >= 1 AND nivel_riesgo <= 7",
            name="ck_estrategia_nivel_riesgo",
        ),
    )

    # ---------------------------------------------------------------------------
    # BLOQUE 1: Datos descriptivos (Tabla 3.28)
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
    # BLOQUE 2: Métricas resumen (Tabla 3.29)
    # Estos campos se rellenan tras la primera ingesta de datos. Cuando un admin
    # crea una estrategia nueva sin datos cargados, todos estos valores son NULL.
    # ---------------------------------------------------------------------------
    retorno_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    volatilidad: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    sortino_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    num_operaciones: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ---------------------------------------------------------------------------
    # BLOQUE 3: Escenarios históricos (Tabla 3.30)
    # Estos campos se rellenan tras la primera ingesta de datos. Cuando un admin
    # crea una estrategia nueva sin datos cargados, todos estos valores son NULL.
    # ---------------------------------------------------------------------------
    mejor_1m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    peor_1m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    mejor_3m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    peor_3m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    mejor_1a: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    peor_1a: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    # Relación 1-N con ResultadoEstrategia: cascade delete para que al borrar
    # una estrategia se eliminen también todos sus resultados históricos.
    resultados: Mapped[list["ResultadoEstrategia"]] = relationship(
        "ResultadoEstrategia",
        back_populates="estrategia",
        cascade="all, delete-orphan",
    )

    # Relación 1-N con Contratacion
    contrataciones: Mapped[list["Contratacion"]] = relationship(
        "Contratacion",
        back_populates="estrategia",
    )
