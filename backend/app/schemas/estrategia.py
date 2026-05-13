"""Schemas Pydantic v2 para la entidad Estrategia."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.estrategia import EstadoEstrategia


class EstrategiaBase(BaseModel):
    """Campos descriptivos de la estrategia (Bloque 1 / Tabla 3.28). Base para Create, Update y Read."""

    nombre: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nombre único de la estrategia.",
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Descripción detallada de la estrategia (opcional).",
    )
    categoria: str = Field(
        ...,
        max_length=50,
        description="Categoría de la estrategia (ej. 'tendencial', 'reversión a la media').",
    )
    tipo_activo: str = Field(
        ...,
        max_length=50,
        description="Tipo de activo sobre el que opera (ej. 'acciones', 'forex', 'cripto').",
    )
    nivel_riesgo: int = Field(
        ...,
        ge=1,
        le=7,
        description="Nivel de riesgo de 1 (muy bajo) a 7 (muy alto).",
    )
    precio_subscripcion: Decimal = Field(
        ...,
        ge=0,
        description="Precio mensual de suscripción en euros. Mínimo 0.",
    )
    comision_ganancias: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Porcentaje de comisión sobre ganancias (0–100).",
    )
    fecha_inicio: date = Field(
        ...,
        description="Fecha de inicio de la estrategia (primer dato histórico disponible).",
    )


class EstrategiaCreate(EstrategiaBase):
    """Payload para crear una nueva estrategia."""

    estado: EstadoEstrategia = Field(
        default=EstadoEstrategia.ACTIVA,
        description="Estado inicial de la estrategia. Por defecto 'activa'.",
    )


class EstrategiaUpdate(BaseModel):
    """Payload para actualizar parcialmente una estrategia (PATCH).

    Las métricas (Bloque 2) y los escenarios (Bloque 3) no se editan
    manualmente; los rellena el módulo de ingesta de datos.
    """

    nombre: Optional[str] = Field(default=None, min_length=3, max_length=100, description="Nombre de la estrategia.")
    descripcion: Optional[str] = Field(default=None, max_length=2000, description="Descripción de la estrategia.")
    categoria: Optional[str] = Field(default=None, max_length=50, description="Categoría de la estrategia.")
    tipo_activo: Optional[str] = Field(default=None, max_length=50, description="Tipo de activo.")
    nivel_riesgo: Optional[int] = Field(default=None, ge=1, le=7, description="Nivel de riesgo (1–7).")
    precio_subscripcion: Optional[Decimal] = Field(default=None, ge=0, description="Precio mensual de suscripción.")
    comision_ganancias: Optional[Decimal] = Field(default=None, ge=0, le=100, description="Comisión sobre ganancias (%).")
    fecha_inicio: Optional[date] = Field(default=None, description="Fecha de inicio de la estrategia.")
    estado: Optional[EstadoEstrategia] = Field(default=None, description="Estado de la estrategia.")


class EstrategiaRead(EstrategiaBase):
    """Representación completa de una estrategia, incluyendo métricas y escenarios calculados."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador único de la estrategia.")
    estado: EstadoEstrategia = Field(..., description="Estado actual: 'activa' o 'pausada'.")
    fecha_creacion: datetime = Field(..., description="Fecha y hora de creación del registro.")
    fecha_ult_actualizacion: datetime = Field(..., description="Fecha y hora de la última modificación.")

    # --- Bloque 2: Métricas resumen (Tabla 3.29) ---
    retorno_total: Optional[Decimal] = Field(default=None, description="Retorno total acumulado de la estrategia.")
    volatilidad: Optional[Decimal] = Field(default=None, description="Volatilidad anualizada.")
    max_drawdown: Optional[Decimal] = Field(default=None, description="Máxima caída desde un pico (drawdown).")
    win_rate: Optional[Decimal] = Field(default=None, description="Porcentaje de operaciones ganadoras (0–1).")
    sortino_ratio: Optional[Decimal] = Field(default=None, description="Ratio Sortino de la estrategia.")
    sharpe_ratio: Optional[Decimal] = Field(default=None, description="Ratio Sharpe de la estrategia.")
    num_operaciones: Optional[int] = Field(default=None, description="Número total de operaciones ejecutadas.")

    # --- Bloque 3: Escenarios históricos (Tabla 3.30) ---
    mejor_1m: Optional[Decimal] = Field(default=None, description="Mejor retorno en ventana de 1 mes.")
    peor_1m: Optional[Decimal] = Field(default=None, description="Peor retorno en ventana de 1 mes.")
    mejor_3m: Optional[Decimal] = Field(default=None, description="Mejor retorno en ventana de 3 meses.")
    peor_3m: Optional[Decimal] = Field(default=None, description="Peor retorno en ventana de 3 meses.")
    mejor_1a: Optional[Decimal] = Field(default=None, description="Mejor retorno en ventana de 1 año.")
    peor_1a: Optional[Decimal] = Field(default=None, description="Peor retorno en ventana de 1 año.")
    activa: bool = Field(..., description="False indica soft delete: la estrategia está desactivada pero sus datos se conservan.")
