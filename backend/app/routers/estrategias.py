"""Router HTTP para el CRUD de estrategias."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.enums import PeriodoEnum
from app.schemas.estrategia import (
    EstrategiaAdminRead,
    EstrategiaCatalogRead,
    EstrategiaCreate,
    EstrategiaDetalleRead,
    EstrategiaRead,
    EstrategiaUpdate,
)
from app.schemas.resultado_estrategia import ResultadoEstrategiaRead
from app.services import estrategia_service
from app.services.metricas_service import obtener_serie_estrategia

router = APIRouter(prefix="/estrategias", tags=["Estrategias"])


@router.post(
    "",
    response_model=EstrategiaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva estrategia (admin)",
    dependencies=[Depends(require_admin)],
)
def crear(
    datos: EstrategiaCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
    """Crea una estrategia. Requiere rol admin.

    Acepta los nuevos campos introducidos en T1.1:
    `codigo_estrategia` (único), `tipo` ('estrategia_activa' | 'benchmark') y
    `fecha_fin` (opcional).
    """
    return estrategia_service.crear_estrategia(db, datos)


@router.get(
    "",
    response_model=list[EstrategiaCatalogRead],
    summary="Catálogo público de estrategias activas",
    description=(
        "Devuelve las estrategias disponibles para contratar, con los cuatro "
        "indicadores clave del periodo OOS (retorno_total_oos, sharpe_oos, "
        "mdd_oos, hit_rate_oos). Los campos *_oos son None si aún no se han "
        "cargado datos.\n\n"
        "Por defecto excluye los benchmarks (índices de referencia). "
        "Activa `incluir_benchmarks=true` para verlos también (útil para el comparador)."
    ),
)
def listar(
    db: Annotated[Session, Depends(get_db)],
    incluir_benchmarks: Annotated[
        bool,
        Query(description="Si true, incluye también los benchmarks (índices de referencia)."),
    ] = False,
) -> list[EstrategiaCatalogRead]:
    return estrategia_service.listar_estrategias(
        db,
        solo_activas=True,
        incluir_benchmarks=incluir_benchmarks,
    )


@router.get(
    "/admin",
    response_model=list[EstrategiaAdminRead],
    summary="Listado completo de estrategias para administrador (RF-12)",
    description=(
        "Devuelve todas las estrategias (activas, pausadas e inactivas), "
        "incluidos benchmarks, con el número de contrataciones activas y "
        "la fecha del último dato histórico disponible en resultado_estrategia. "
        "Requiere rol admin."
    ),
    dependencies=[Depends(require_admin)],
)
def listar_admin(
    db: Annotated[Session, Depends(get_db)],
) -> list[EstrategiaAdminRead]:
    return estrategia_service.listar_estrategias_admin(db)


@router.get(
    "/{id_estrategia}",
    response_model=EstrategiaDetalleRead,
    summary="Detalle de una estrategia con métricas completas (dev y oos)",
    description=(
        "Devuelve todos los campos descriptivos de la estrategia junto con "
        "la lista completa de métricas por periodo (dev/oos). "
        "El array `metricas` está vacío si aún no se han cargado datos."
    ),
)
def detalle(
    id_estrategia: int,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaDetalleRead:
    estrategia = estrategia_service.obtener_estrategia_por_id(
        db, id_estrategia, solo_activas=True
    )
    if estrategia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada.",
        )
    return estrategia


@router.patch(
    "/{id_estrategia}",
    response_model=EstrategiaRead,
    summary="Actualizar parcialmente una estrategia (admin)",
    dependencies=[Depends(require_admin)],
)
def actualizar(
    id_estrategia: int,
    datos: EstrategiaUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
    estrategia = estrategia_service.actualizar_estrategia(db, id_estrategia, datos)
    if estrategia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada.",
        )
    return estrategia


@router.delete(
    "/{id_estrategia}",
    response_model=EstrategiaRead,
    summary=(
        "Dar de baja una estrategia (soft delete con cancelación en cascada "
        "de contrataciones activas y devolución de saldo a los usuarios afectados)"
    ),
    dependencies=[Depends(require_admin)],
)
def dar_de_baja(
    id_estrategia: int,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
    estrategia = estrategia_service.dar_de_baja_estrategia(db, id_estrategia)
    if estrategia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada.",
        )
    return estrategia


@router.get(
    "/{id_estrategia}/resultados",
    response_model=list[ResultadoEstrategiaRead],
    summary="Serie temporal de resultados de una estrategia",
    description=(
        "Devuelve la serie diaria de equity, retorno y drawdown de una estrategia. "
        "Filtra por `periodo` ('dev' o 'oos'); si se omite devuelve ambos periodos. "
        "Permite acotar el rango con `desde` y `hasta` (formato YYYY-MM-DD, ambos inclusivos)."
    ),
)
def listar_resultados_estrategia(
    id_estrategia: int,
    db: Annotated[Session, Depends(get_db)],
    periodo: Annotated[
        Optional[PeriodoEnum],
        Query(description="Periodo a consultar: 'dev' (in-sample) u 'oos' (out-of-sample). Omitir para ambos."),
    ] = None,
    desde: Annotated[
        Optional[str],
        Query(description="Fecha mínima (inclusiva), formato YYYY-MM-DD."),
    ] = None,
    hasta: Annotated[
        Optional[str],
        Query(description="Fecha máxima (inclusiva), formato YYYY-MM-DD."),
    ] = None,
) -> list[ResultadoEstrategiaRead]:
    from datetime import date as date_type

    def parse_date(s: Optional[str]) -> Optional[date_type]:
        return date_type.fromisoformat(s) if s else None

    serie = obtener_serie_estrategia(
        db,
        id_estrategia,
        periodo=periodo.value if periodo else None,
        desde=parse_date(desde),
        hasta=parse_date(hasta),
    )
    if serie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada.",
        )
    return serie
