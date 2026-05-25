"""Schemas Pydantic para el endpoint de ingesta de paquetes.

Jerarquía de respuesta
----------------------
IngestaResponseSchema
├── status : "ok" | "error"
├── summary : IngestaSummarySchema | None
│     ├── estrategias_creadas : int
│     ├── metricas_creadas    : int
│     └── resultados_creados  : int
└── errores : list[IngestaErrorSchema]
      ├── archivo  : str
      ├── fila     : int | None
      ├── columna  : str | None
      ├── codigo   : str
      ├── mensaje  : str
      └── nivel    : str  ("error" | "warning")
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class IngestaErrorSchema(BaseModel):
    """Representa un único problema detectado durante la validación o persistencia."""

    archivo: str
    fila: int | None = None
    columna: str | None = None
    codigo: str
    mensaje: str
    nivel: str = "error"

    model_config = {"from_attributes": True}


class IngestaSummarySchema(BaseModel):
    """Recuento de entidades creadas tras una ingesta exitosa."""

    estrategias_creadas: int
    metricas_creadas: int
    resultados_creados: int


class IngestaResponseSchema(BaseModel):
    """Respuesta unificada del endpoint POST /admin/ingesta/paquete.

    - Si ``status == "ok"``, ``summary`` contiene los recuentos y ``errores``
      puede contener warnings (nivel='warning') pero no errores bloqueantes.
    - Si ``status == "error"``, ``summary`` es None y ``errores`` contiene al
      menos un elemento con nivel='error'.
    """

    status: Literal["ok", "error"]
    summary: IngestaSummarySchema | None = None
    errores: list[IngestaErrorSchema] = []
