"""Schemas Pydantic v2 para la entidad ResultadoEstrategia."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResultadoEstrategiaBase(BaseModel):
    """Campos de un resultado diario de estrategia. Base para Create y Read."""

    id_estrategia: int = Field(
        ...,
        description="ID de la estrategia a la que pertenece este resultado.",
    )
    fecha: date = Field(
        ...,
        description="Fecha del punto de datos (un registro por día por estrategia).",
    )
    equity: Decimal = Field(
        ...,
        description="Valor del equity de la estrategia en esta fecha.",
    )
    drawdown: Decimal = Field(
        ...,
        le=0,
        description="Caída acumulada desde el máximo previo. Siempre <= 0.",
    )
    retorno: Decimal = Field(
        ...,
        description="Retorno diario de la estrategia.",
    )
    sharpe_ratio: Optional[Decimal] = Field(
        default=None,
        description="Sharpe Rolling calculado sobre ventana histórica. Null hasta acumular datos suficientes.",
    )


class ResultadoEstrategiaCreate(ResultadoEstrategiaBase):
    """Payload de ingesta de un resultado diario. Idéntico al Base; se separa para claridad semántica."""


class ResultadoEstrategiaRead(ResultadoEstrategiaBase):
    """Representación de un resultado diario leído desde la base de datos."""

    model_config = ConfigDict(from_attributes=True)
