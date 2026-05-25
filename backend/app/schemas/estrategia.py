"""Schemas Pydantic v2 para la entidad Estrategia."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TipoEstrategia
from app.models.estrategia import EstadoEstrategia
# Import diferido para evitar ciclos: metrica_estrategia -> enums (sin ciclo real,
# pero se importa aquí abajo junto a los schemas que lo usan).
from app.schemas.metrica_estrategia import MetricaEstrategiaRead


class EstrategiaBase(BaseModel):
    """Campos descriptivos de la estrategia. Base para Create, Update y Read.

    PRINCIPIO: este schema NO contiene field_validators con reglas de negocio
    sobre input del cliente (p.ej. "fecha_inicio no puede ser futura"). Esas
    reglas van SOLAMENTE en EstrategiaCreate y EstrategiaUpdate para que las
    respuestas GET nunca fallen la validación por datos históricos válidos.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

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
    # --- Nuevos campos T1.1 ---
    codigo_estrategia: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código único legible por humanos (ej. 'SP500_MOM_2024').",
    )
    tipo: TipoEstrategia = Field(
        ...,
        description="Tipo de estrategia: 'estrategia_activa' o 'benchmark'.",
    )
    fecha_fin: Optional[date] = Field(
        default=None,
        description="Fecha de cierre de la estrategia. None si sigue activa.",
    )


class EstrategiaCreate(EstrategiaBase):
    """Payload para crear una nueva estrategia."""

    estado: EstadoEstrategia = Field(
        default=EstadoEstrategia.ACTIVA,
        description="Estado inicial de la estrategia. Por defecto 'activa'.",
    )

    @field_validator("fecha_inicio")
    @classmethod
    def fecha_inicio_no_futuro(cls, v: date) -> date:
        """fecha_inicio representa el primer dato histórico disponible
        de la estrategia, por lo que no tiene sentido que sea futura.
        """
        if v > date.today():
            raise ValueError("La fecha de inicio no puede estar en el futuro.")
        return v


class EstrategiaUpdate(BaseModel):
    """Payload para actualizar parcialmente una estrategia (PATCH).

    Todos los campos son opcionales. Las métricas resumen viven ahora en
    MetricaEstrategia y no se editan desde este endpoint.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: Optional[str] = Field(default=None, min_length=3, max_length=100, description="Nombre de la estrategia.")
    descripcion: Optional[str] = Field(default=None, max_length=2000, description="Descripción de la estrategia.")
    categoria: Optional[str] = Field(default=None, max_length=50, description="Categoría de la estrategia.")
    tipo_activo: Optional[str] = Field(default=None, max_length=50, description="Tipo de activo.")
    nivel_riesgo: Optional[int] = Field(default=None, ge=1, le=7, description="Nivel de riesgo (1–7).")
    precio_subscripcion: Optional[Decimal] = Field(default=None, ge=0, description="Precio mensual de suscripción.")
    comision_ganancias: Optional[Decimal] = Field(default=None, ge=0, le=100, description="Comisión sobre ganancias (%).")
    fecha_inicio: Optional[date] = Field(default=None, description="Fecha de inicio de la estrategia.")
    estado: Optional[EstadoEstrategia] = Field(default=None, description="Estado de la estrategia.")
    codigo_estrategia: Optional[str] = Field(default=None, min_length=1, max_length=50, description="Código único de la estrategia.")
    tipo: Optional[TipoEstrategia] = Field(default=None, description="Tipo: 'estrategia_activa' o 'benchmark'.")
    fecha_fin: Optional[date] = Field(default=None, description="Fecha de cierre de la estrategia.")

    @field_validator("fecha_inicio")
    @classmethod
    def fecha_inicio_no_futuro(cls, v: Optional[date]) -> Optional[date]:
        """Si se actualiza fecha_inicio, no puede quedar en el futuro."""
        if v is not None and v > date.today():
            raise ValueError("La fecha de inicio no puede estar en el futuro.")
        return v


class EstrategiaRead(EstrategiaBase):
    """Representación completa de una estrategia para respuestas de la API.

    Hereda todos los campos descriptivos de EstrategiaBase (incluidos los nuevos
    codigo_estrategia, tipo y fecha_fin añadidos en T1.1).
    Las métricas de rendimiento están en MetricaEstrategiaRead.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador único de la estrategia.")
    estado: EstadoEstrategia = Field(..., description="Estado actual: 'activa' o 'pausada'.")
    fecha_creacion: datetime = Field(..., description="Fecha y hora de creación del registro.")
    fecha_ult_actualizacion: datetime = Field(..., description="Fecha y hora de la última modificación.")
    activa: bool = Field(
        ...,
        description="False indica soft delete: la estrategia está desactivada pero sus datos se conservan.",
    )


class EstrategiaAdminRead(EstrategiaRead):
    """Vista de administrador de una estrategia (RF-12).

    Extiende EstrategiaRead con dos campos agregados calculados en consulta.
    Incluye estrategias inactivas (activa=False).
    Las métricas (cagr, sharpe, etc.) NO se incluyen aquí: viven en MetricaEstrategiaRead.
    El campo `tipo` ya está presente por herencia desde EstrategiaBase.
    """

    num_contrataciones_activas: int = Field(
        ...,
        description="Número de usuarios con contratación activa sobre esta estrategia.",
    )
    fecha_ultima_actualizacion: Optional[date] = Field(
        default=None,
        description="Fecha del dato más reciente en resultado_estrategia. None si no hay datos cargados.",
    )


class EstrategiaCatalogRead(EstrategiaRead):
    """Estrategia con resumen de métricas OOS para el catálogo público.

    Extiende EstrategiaRead con cuatro indicadores clave del periodo out-of-sample.
    Todos son None cuando la estrategia aún no tiene métricas OOS cargadas
    (estado inicial vacío, antes de la primera ingesta de datos).
    Solo muestra estrategias de tipo 'estrategia_activa' (no benchmarks).
    """

    retorno_total_oos: Optional[Decimal] = Field(
        default=None,
        description="Retorno total acumulado en el periodo OOS. None si aún no hay datos.",
    )
    sharpe_oos: Optional[Decimal] = Field(
        default=None,
        description="Ratio de Sharpe anualizado en el periodo OOS. None si aún no hay datos.",
    )
    mdd_oos: Optional[Decimal] = Field(
        default=None,
        description="Máximo drawdown en el periodo OOS (valor negativo). None si aún no hay datos.",
    )
    hit_rate_oos: Optional[Decimal] = Field(
        default=None,
        description="Porcentaje de operaciones ganadoras en OOS (0–1). None si aún no hay datos.",
    )


class EstrategiaDetalleRead(EstrategiaRead):
    """Estrategia con todas sus métricas (dev y oos) para la vista de detalle.

    Extiende EstrategiaRead con la lista completa de MetricaEstrategiaRead,
    ordenada por periodo. Lista vacía cuando la estrategia aún no tiene
    métricas cargadas.
    """

    metricas: list[MetricaEstrategiaRead] = Field(
        default_factory=list,
        description="Métricas de rendimiento por periodo (dev/oos). Vacío si no hay datos.",
    )
