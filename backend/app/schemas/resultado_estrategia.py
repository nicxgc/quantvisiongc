"""Schemas Pydantic v2 para la entidad ResultadoEstrategia.

ResultadoEstrategia no se crea ni se actualiza a través de la API REST:
las filas las inserta el módulo de ingesta de datos. Por eso solo se
define el schema Read.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PeriodoEnum


class ResultadoEstrategiaRead(BaseModel):
    """Una observación diaria de los resultados de una estrategia en un periodo (dev/oos).

    Corresponde a una fila de la hypertable resultado_estrategia.
    PK compuesta: (id_estrategia, periodo, fecha).
    """

    model_config = ConfigDict(from_attributes=True)

    id_estrategia: int = Field(
        ...,
        description="Identificador de la estrategia a la que pertenece esta observación.",
    )
    periodo: PeriodoEnum = Field(
        ...,
        description="Periodo de evaluación: 'dev' (in-sample) u 'oos' (out-of-sample).",
    )
    fecha: date = Field(
        ...,
        description="Fecha de la observación.",
    )
    equity: Decimal = Field(
        ...,
        description="Nivel acumulado del capital en esa fecha.",
    )
    retorno: Decimal = Field(
        ...,
        description="Retorno simple del día respecto al equity del día anterior.",
    )
    drawdown: Decimal = Field(
        ...,
        description="Caída desde el máximo histórico alcanzado hasta esa fecha. Valor en [-1, 0].",
    )
