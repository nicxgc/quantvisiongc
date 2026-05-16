"""Schemas Pydantic v2 para la entidad Contratacion."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.contratacion import EstadoContratacion


class ContratacionBase(BaseModel):
    """Campos compartidos en operaciones sobre contrataciones."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_estrategia: int = Field(
        ...,
        gt=0,
        description="ID de la estrategia que se desea contratar.",
    )


class ContratacionCreate(ContratacionBase):
    """Payload para crear una contratación.

    El campo monto_invertido se deriva del precio_subscripcion de la
    estrategia en el servicio, no se recibe del cliente.
    """


class ContratacionUpdate(BaseModel):
    """Vacío a propósito: la cancelación tiene su propio endpoint
    dedicado (PATCH /contrataciones/{id}/cancelar), no se hace por
    PATCH genérico.
    """


class ContratacionRead(ContratacionBase):
    """Representación completa de una contratación."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int = Field(..., description="Identificador único de la contratación.")
    id_usuario: int = Field(..., description="ID del usuario que realizó la contratación.")
    monto_invertido: Decimal = Field(
        ...,
        description="Cantidad en euros invertida en el momento de contratar.",
    )
    fecha_contratacion: datetime = Field(
        ...,
        description="Fecha y hora en que se realizó la contratación.",
    )
    fecha_cancelacion: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora de cancelación. None si la contratación sigue activa.",
    )
    estado: EstadoContratacion = Field(
        ...,
        description="Estado actual: 'activa' o 'cancelada'.",
    )
