"""Schemas Pydantic v2 para los DTOs del dashboard de usuario."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DashboardKPIs(BaseModel):
    """KPIs agregados del usuario para la vista principal del dashboard.

    Resume el estado del monedero y de todas las contrataciones activas,
    valoradas al último equity disponible de cada estrategia contratada.
    """

    model_config = ConfigDict(from_attributes=True)

    saldo_monedero: Decimal = Field(
        ...,
        description="Saldo disponible en el monedero ficticio del usuario.",
    )
    total_invertido: Decimal = Field(
        ...,
        description="Suma del monto_invertido en todas las contrataciones activas del usuario.",
    )
    valor_actual: Decimal = Field(
        ...,
        description="Valor actual total de las inversiones, calculado escalando cada monto invertido por el crecimiento del equity de la estrategia desde su fecha de contratación.",
    )
    pnl_absoluto: Decimal = Field(
        ...,
        description="Resultado absoluto en euros: valor_actual - total_invertido.",
    )
    rentabilidad_total: Decimal = Field(
        ...,
        description="Rentabilidad relativa total: pnl_absoluto / total_invertido. Devuelve 0 si total_invertido es 0.",
    )
    num_estrategias_activas: int = Field(
        ...,
        description="Número de contrataciones del usuario actualmente activas.",
    )


class AccionReciente(BaseModel):
    """Un evento de actividad del usuario en el dashboard (RF-27).

    Cada contratación produce un evento 'contratacion' y, si se cancela,
    un evento 'cancelacion' adicional e independiente.
    """

    model_config = ConfigDict(from_attributes=True)

    tipo: Literal["contratacion", "cancelacion"] = Field(
        ..., description="Tipo de evento: 'contratacion' al contratar, 'cancelacion' al cancelar."
    )
    fecha: datetime = Field(..., description="Fecha y hora del evento.")
    nombre_estrategia: str = Field(..., description="Nombre de la estrategia involucrada.")
    monto: Decimal = Field(
        ..., description="Importe en euros (siempre positivo). El tipo indica la dirección del flujo."
    )
