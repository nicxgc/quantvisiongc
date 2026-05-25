"""Definiciones de tipos ENUM reutilizables entre modelos SQLAlchemy y schemas Pydantic.

Cada tipo tiene dos representaciones:
  - PgEnum (SQLAlchemy / PostgreSQL): con create_type=False para que Alembic
    los cree explícitamente en cada migración y evite errores DuplicateObject.
  - str + enum.Enum (Python / Pydantic): para usar en field_validator y anotaciones
    de tipo en los schemas de respuesta.
"""

import enum

from sqlalchemy.dialects.postgresql import ENUM as PgEnum


# ---------------------------------------------------------------------------
# TipoEstrategia
# ---------------------------------------------------------------------------

class TipoEstrategia(str, enum.Enum):
    """Distingue entre estrategias reales (activas) y benchmarks de referencia."""
    ESTRATEGIA_ACTIVA = "estrategia_activa"
    BENCHMARK = "benchmark"


# PgEnum reutilizable en mapped_column() y en las migraciones Alembic.
tipo_estrategia_enum = PgEnum(
    "estrategia_activa",
    "benchmark",
    name="tipo_estrategia_enum",
    create_type=False,
)


# ---------------------------------------------------------------------------
# PeriodoEnum
# ---------------------------------------------------------------------------

class PeriodoEnum(str, enum.Enum):
    """Periodo de evaluación de resultados y métricas: dev (in-sample) u oos (out-of-sample)."""
    DEV = "dev"
    OOS = "oos"


# PgEnum reutilizable en mapped_column() y en las migraciones Alembic.
periodo_enum = PgEnum(
    "dev",
    "oos",
    name="periodo_enum",
    create_type=False,
)
