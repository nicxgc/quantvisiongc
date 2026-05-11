"""Modelo ORM para la entidad Contratacion. Corresponde a la Tabla 3.32 de la memoria."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.estrategia import Estrategia
    from app.models.usuario import Usuario


class EstadoContratacion(str, enum.Enum):
    ACTIVA = "activa"
    CANCELADA = "cancelada"


class Contratacion(Base):
    """Corresponde a la Tabla 3.32 de la memoria.

    Entidad asociativa con atributos propios que relaciona Usuario con
    Estrategia y registra el ciclo de vida de la suscripción.
    """

    __tablename__ = "contratacion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ON DELETE RESTRICT en ambas FK: borrar un usuario o una estrategia que
    # tenga contrataciones vinculadas es semánticamente sospechoso y podría
    # implicar pérdida de datos de auditoría. RESTRICT obliga al admin a
    # cancelar explícitamente las contrataciones antes de eliminar el registro
    # padre, evitando borrados accidentales con consecuencias irreversibles.
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"),
        index=True,
    )
    id_estrategia: Mapped[int] = mapped_column(
        ForeignKey("estrategia.id", ondelete="RESTRICT"),
        index=True,
    )

    fecha_contratacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    fecha_cancelacion: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estado: Mapped[EstadoContratacion] = mapped_column(
        Enum(EstadoContratacion, name="estado_contratacion",
             values_callable=lambda x: [e.value for e in x]),
        default=EstadoContratacion.ACTIVA,
        index=True,
    )

    # Relaciones N-1
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="contrataciones",
    )
    estrategia: Mapped["Estrategia"] = relationship(
        "Estrategia",
        back_populates="contrataciones",
    )
