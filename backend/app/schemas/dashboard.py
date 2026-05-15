"""Schemas Pydantic v2 para los DTOs del dashboard de usuario."""

from decimal import Decimal

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
