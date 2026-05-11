"""Modelo ORM para la entidad ResultadoEstrategia. Corresponde a la Tabla 3.31 de la memoria."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.estrategia import Estrategia


class ResultadoEstrategia(Base):
    """Corresponde a la Tabla 3.31 de la memoria.

    Entidad débil con PK compuesta (id_estrategia, fecha). Cada fila recoge
    el estado del equity y métricas de rendimiento de una estrategia en una
    fecha concreta.
    """

    __tablename__ = "resultado_estrategia"

    __table_args__ = (
        PrimaryKeyConstraint("id_estrategia", "fecha", name="pk_resultado_estrategia"),
    )

    # FK a estrategia con ON DELETE CASCADE: si se borra la estrategia padre,
    # todos sus resultados históricos se eliminan en cascada.
    id_estrategia: Mapped[int] = mapped_column(
        ForeignKey("estrategia.id", ondelete="CASCADE"),
    )
    fecha: Mapped[date] = mapped_column(Date)

    equity: Mapped[Decimal] = mapped_column(Numeric(15, 6))
    drawdown: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    retorno: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    # Sharpe Rolling: requiere una ventana mínima de datos históricos para
    # calcularse, por eso es nullable en las primeras filas de una serie.
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    # Relación N-1 con Estrategia
    estrategia: Mapped["Estrategia"] = relationship(
        "Estrategia",
        back_populates="resultados",
    )
