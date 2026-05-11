"""Schemas Pydantic v2 para la entidad Contratacion."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.contratacion import EstadoContratacion


class ContratacionBase(BaseModel):
    """Campo mínimo compartido para contratar una estrategia.

    id_usuario no se incluye aquí: se extrae del JWT en el endpoint
    para evitar que un usuario pueda contratar en nombre de otro.
    """

    id_estrategia: int = Field(
        ...,
        description="ID de la estrategia que se desea contratar.",
    )


class ContratacionCreate(ContratacionBase):
    """Payload para crear una nueva contratación. Solo requiere el ID de la estrategia."""


class ContratacionRead(ContratacionBase):
    """Representación completa de una contratación leída desde la base de datos."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador único de la contratación.")
    id_usuario: int = Field(..., description="ID del usuario que realizó la contratación.")
    fecha_contratacion: datetime = Field(..., description="Fecha y hora en que se realizó la contratación.")
    fecha_cancelacion: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora de cancelación. Null si la contratación sigue activa.",
    )
    estado: EstadoContratacion = Field(..., description="Estado actual: 'activa' o 'cancelada'.")
