"""Schemas Pydantic v2 para el monedero virtual del usuario (RF-46, RF-47)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.models.movimiento_monedero import TipoMovimiento

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import CANTIDADES_RECARGA_PERMITIDAS


class MonederoIngresoCreate(BaseModel):
    """Payload para recargar el monedero. Solo acepta denominaciones predefinidas."""

    cantidad: Decimal = Field(
        ...,
        description="Cantidad a ingresar. Debe ser una denominación válida.",
    )

    @field_validator("cantidad")
    @classmethod
    def cantidad_en_conjunto_permitido(cls, v: Decimal) -> Decimal:
        """Rechaza cantidades que no estén en el conjunto de denominaciones permitidas."""
        if v not in CANTIDADES_RECARGA_PERMITIDAS:
            permitidas = ", ".join(str(c) for c in CANTIDADES_RECARGA_PERMITIDAS)
            raise ValueError(
                f"La cantidad {v} no está permitida. Cantidades válidas: {permitidas}"
            )
        return v


class MovimientoMonederoRead(BaseModel):
    """Representación de un movimiento del monedero (RF-47)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador único del movimiento.")
    tipo: TipoMovimiento = Field(
        ..., description="Tipo de operación que originó el movimiento."
    )
    monto: Decimal = Field(
        ..., description="Importe del movimiento (siempre positivo)."
    )
    saldo_resultante: Decimal = Field(
        ..., description="Saldo del monedero tras aplicar este movimiento."
    )
    fecha: datetime = Field(..., description="Fecha y hora del movimiento con timezone.")
    id_contratacion: Optional[int] = Field(
        default=None,
        description="ID de la contratación vinculada, si aplica.",
    )


class MonederoRecargaResponse(BaseModel):
    """Respuesta completa del endpoint de recarga del monedero (RF-46)."""

    model_config = ConfigDict(from_attributes=True)

    saldo_anterior: Decimal = Field(..., description="Saldo antes de la recarga.")
    cantidad_ingresada: Decimal = Field(..., description="Cantidad ingresada.")
    saldo_actual: Decimal = Field(..., description="Saldo resultante tras la recarga.")
    movimiento: MovimientoMonederoRead = Field(
        ..., description="Registro del movimiento creado."
    )


class CantidadesPermitidasResponse(BaseModel):
    """Lista de denominaciones válidas para recargar el monedero."""

    cantidades: list[Decimal] = Field(
        ..., description="Denominaciones permitidas en euros."
    )
