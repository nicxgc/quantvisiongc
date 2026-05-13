"""Router HTTP para el CRUD de estrategias."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.estrategia import EstrategiaCreate, EstrategiaRead, EstrategiaUpdate
from app.services import estrategia_service

router = APIRouter(prefix="/estrategias", tags=["Estrategias"])


@router.post(
    "",
    response_model=EstrategiaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva estrategia",
    dependencies=[Depends(require_admin)],
)
def crear(
    datos: EstrategiaCreate,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
    try:
        return estrategia_service.crear_estrategia(db, datos)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "",
    response_model=list[EstrategiaRead],
    summary="Listar el catálogo público de estrategias activas",
)
def listar(
    db: Annotated[Session, Depends(get_db)],
) -> list[EstrategiaRead]:
    return estrategia_service.listar_estrategias(db, solo_activas=True)


@router.get(
    "/{id_estrategia}",
    response_model=EstrategiaRead,
    summary="Obtener el detalle de una estrategia",
)
def detalle(
    id_estrategia: int,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
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
    summary="Actualizar parcialmente una estrategia",
    dependencies=[Depends(require_admin)],
)
def actualizar(
    id_estrategia: int,
    datos: EstrategiaUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> EstrategiaRead:
    try:
        estrategia = estrategia_service.actualizar_estrategia(db, id_estrategia, datos)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
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
