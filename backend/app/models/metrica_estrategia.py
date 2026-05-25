"""Modelo ORM para la entidad MetricaEstrategia.

Almacena las métricas resumen de rendimiento de una estrategia para un periodo
concreto (dev / oos). PK compuesta (id_estrategia, periodo).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import periodo_enum

if TYPE_CHECKING:
    from app.models.estrategia import Estrategia


class MetricaEstrategia(Base):
    """Métricas de rendimiento por estrategia y periodo (dev/oos)."""

    __tablename__ = "metrica_estrategia"

    __table_args__ = (
        PrimaryKeyConstraint("id_estrategia", "periodo", name="pk_metrica_estrategia"),
    )

    id_estrategia: Mapped[int] = mapped_column(
        ForeignKey("estrategia.id", ondelete="CASCADE"),
    )
    periodo: Mapped[str] = mapped_column(periodo_enum, nullable=False)

    # Ventana temporal del periodo evaluado
    fecha_inicio_periodo: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_periodo: Mapped[date] = mapped_column(Date, nullable=False)

    # Métricas de rendimiento
    retorno_total: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    cagr: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    volatility: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    sharpe: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    sortino: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    calmar: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    mdd: Mapped[Decimal] = mapped_column(Numeric(10, 4))

    # Métricas opcionales (pueden no estar disponibles para todos los periodos)
    n_trades: Mapped[Optional[int]] = mapped_column(nullable=True)
    hit_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    profit_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    # Relación N-1 con Estrategia
    estrategia: Mapped["Estrategia"] = relationship(
        "Estrategia",
        back_populates="metricas",
    )
