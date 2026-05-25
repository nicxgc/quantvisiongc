"""Modelo ORM para la entidad ResultadoEstrategia.

Serie temporal de equity/drawdown/retorno diario por estrategia y periodo (dev/oos).
Almacenada como hypertable de TimescaleDB particionada por fecha.
PK compuesta: (id_estrategia, periodo, fecha).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import periodo_enum

if TYPE_CHECKING:
    from app.models.estrategia import Estrategia


class ResultadoEstrategia(Base):
    """Serie temporal diaria de una estrategia para un periodo concreto (dev u oos).

    Entidad débil con PK compuesta (id_estrategia, periodo, fecha).
    """

    __tablename__ = "resultado_estrategia"

    __table_args__ = (
        PrimaryKeyConstraint(
            "id_estrategia", "periodo", "fecha",
            name="pk_resultado_estrategia",
        ),
    )

    # FK a estrategia con ON DELETE CASCADE.
    id_estrategia: Mapped[int] = mapped_column(
        ForeignKey("estrategia.id", ondelete="CASCADE"),
    )
    # Periodo de evaluación: 'dev' (in-sample) u 'oos' (out-of-sample).
    periodo: Mapped[str] = mapped_column(periodo_enum, nullable=False)
    fecha: Mapped[date] = mapped_column(Date)

    equity: Mapped[Decimal] = mapped_column(Numeric(15, 6))
    drawdown: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    retorno: Mapped[Decimal] = mapped_column(Numeric(10, 6))

    # Relación N-1 con Estrategia
    estrategia: Mapped["Estrategia"] = relationship(
        "Estrategia",
        back_populates="resultados",
    )
