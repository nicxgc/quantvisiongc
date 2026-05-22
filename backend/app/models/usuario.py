"""Modelo ORM para la entidad Usuario. Corresponde a la Tabla 3.27 de la memoria."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.contratacion import Contratacion
    from app.models.movimiento_monedero import MovimientoMonedero


class RolUsuario(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class Usuario(Base):
    """Corresponde a la Tabla 3.27 de la memoria."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_completo: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, name="rol_usuario",
             values_callable=lambda x: [e.value for e in x]),
        default=RolUsuario.USER,
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    saldo_monedero: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default="0.00",
    )
    # Soft delete: False bloquea el acceso sin borrar la fila ni su historial.
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relación 1-N: un usuario puede tener varias contrataciones
    contrataciones: Mapped[list["Contratacion"]] = relationship(
        "Contratacion",
        back_populates="usuario",
    )

    # Relación 1-N: un usuario puede tener varios movimientos de monedero
    movimientos: Mapped[list["MovimientoMonedero"]] = relationship(
        "MovimientoMonedero",
        back_populates="usuario",
    )
