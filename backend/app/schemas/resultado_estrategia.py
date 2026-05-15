"""Schemas Pydantic v2 para la entidad ResultadoEstrategia.

A diferencia de otras entidades, ResultadoEstrategia no se crea ni se
actualiza a través de la API REST: las filas las inserta el script de
seed (y en el futuro un módulo de ingesta de datos). Por eso solo se
define el schema Read.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResultadoEstrategiaRead(BaseModel):
    """Una observación diaria de los resultados de una estrategia.

    Corresponde a una fila de la tabla resultado_estrategia (Tabla 3.31).
    """

    model_config = ConfigDict(from_attributes=True)

    id_estrategia: int = Field(
        ...,
        description="Identificador de la estrategia a la que pertenece esta observación.",
    )
    fecha: date = Field(
        ...,
        description="Fecha de la observación.",
    )
    equity: Decimal = Field(
        ...,
        description="Nivel acumulado del capital en esa fecha, partiendo de 10.000 €.",
    )
    retorno: Decimal = Field(
        ...,
        description="Retorno simple del día, calculado respecto al equity del día anterior.",
    )
    drawdown: Decimal = Field(
        ...,
        description="Caída desde el máximo histórico alcanzado hasta esa fecha. Valor en [-1, 0].",
    )
    sharpe_ratio: Optional[Decimal] = Field(
        default=None,
        description="Sharpe ratio rolling anualizado sobre ventana de 30 días. NULL durante el periodo de calentamiento.",
    )
