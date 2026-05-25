"""Schemas Pydantic v2 para la entidad MetricaEstrategia.

MetricaEstrategia almacena las métricas de rendimiento de una estrategia
para un periodo concreto (dev / oos). Solo se define el schema Read porque
las métricas se insertan vía el módulo de ingesta de datos, no a través de
la API REST de gestión.

Preparado para añadir MetricaEstrategiaCreate y MetricaEstrategiaUpdate
cuando se implemente T2 (importación de resultados).
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PeriodoEnum


class MetricaEstrategiaBase(BaseModel):
    """Campos comunes de MetricaEstrategia."""

    model_config = ConfigDict(str_strip_whitespace=True)

    periodo: PeriodoEnum = Field(
        ...,
        description="Periodo de evaluación: 'dev' (in-sample) u 'oos' (out-of-sample).",
    )
    fecha_inicio_periodo: date = Field(
        ...,
        description="Primera fecha del rango temporal evaluado.",
    )
    fecha_fin_periodo: date = Field(
        ...,
        description="Última fecha del rango temporal evaluado.",
    )

    # --- Métricas de rendimiento ---
    retorno_total: Decimal = Field(..., description="Retorno total acumulado en el periodo.")
    cagr: Decimal = Field(..., description="Tasa de crecimiento anual compuesta (CAGR).")
    volatility: Decimal = Field(..., description="Volatilidad anualizada.")
    sharpe: Decimal = Field(..., description="Ratio de Sharpe anualizado.")
    sortino: Decimal = Field(..., description="Ratio de Sortino anualizado.")
    calmar: Decimal = Field(..., description="Ratio de Calmar (CAGR / MDD).")
    mdd: Decimal = Field(..., description="Máximo drawdown (caída desde pico) en el periodo.")

    # --- Métricas opcionales (pueden no estar disponibles para todos los periodos) ---
    n_trades: Optional[int] = Field(default=None, description="Número de operaciones en el periodo.")
    hit_rate: Optional[Decimal] = Field(default=None, description="Porcentaje de operaciones ganadoras (0–1).")
    profit_factor: Optional[Decimal] = Field(default=None, description="Ratio ganancia bruta / pérdida bruta.")


class MetricaEstrategiaRead(MetricaEstrategiaBase):
    """Representación completa de las métricas de una estrategia para un periodo."""

    model_config = ConfigDict(from_attributes=True)

    id_estrategia: int = Field(
        ...,
        description="Identificador de la estrategia a la que pertenecen estas métricas.",
    )
