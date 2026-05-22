"""Modelo ORM para la entidad MovimientoMonedero.

Registra cada movimiento (entrada o salida) del monedero virtual de un usuario,
permitiendo reconstruir el histórico completo y el saldo en cualquier punto.
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contratacion import Contratacion
    from app.models.usuario import Usuario


class TipoMovimiento(str, enum.Enum):
    INGRESO = "ingreso"
    CONTRATACION = "contratacion"
    CANCELACION = "cancelacion"


class MovimientoMonedero(Base):
    """Histórico de movimientos del monedero virtual de un usuario.

    Cada fila representa un evento atómico que modifica el saldo:
    - 'ingreso': recarga manual del monedero.
    - 'contratacion': descuento al contratar una estrategia.
    - 'cancelacion': devolución al cancelar una contratación.

    El campo `monto` es siempre positivo; el tipo determina la dirección del flujo.
    """

    __tablename__ = "movimiento_monedero"

    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_movimiento_monto_positivo"),
        # Índice compuesto para la consulta de histórico cronológico inverso por usuario (RF-47).
        Index("idx_movimiento_usuario_fecha", "id_usuario", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"),
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(
        Enum(
            TipoMovimiento,
            name="tipo_movimiento",
            values_callable=lambda x: [e.value for e in x],
        ),
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    # FK opcional: solo presente en movimientos vinculados a una contratación.
    id_contratacion: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contratacion.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relaciones
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="movimientos",
    )
    contratacion: Mapped[Optional["Contratacion"]] = relationship(
        "Contratacion",
    )
