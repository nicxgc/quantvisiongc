"""Router del monedero virtual del usuario autenticado (RF-46, RF-47)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import CANTIDADES_RECARGA_PERMITIDAS
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.monedero import (
    CantidadesPermitidasResponse,
    MonederoIngresoCreate,
    MonederoRecargaResponse,
    MovimientoMonederoRead,
)
from app.services import monedero_service

router = APIRouter(prefix="/users/me/monedero", tags=["monedero"])


@router.get(
    "/cantidades-permitidas",
    response_model=CantidadesPermitidasResponse,
    summary="Lista de denominaciones válidas para la recarga del monedero",
    description="Devuelve el conjunto cerrado de cantidades permitidas para la recarga (RF-46). "
                "El frontend debe usar esta lista en lugar de hardcodearla.",
)
def cantidades_permitidas(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> CantidadesPermitidasResponse:
    return CantidadesPermitidasResponse(cantidades=list(CANTIDADES_RECARGA_PERMITIDAS))


@router.post(
    "/recargar",
    response_model=MonederoRecargaResponse,
    status_code=status.HTTP_200_OK,
    summary="Recargar el monedero virtual (RF-46)",
    description="Ingresa una cantidad del conjunto de denominaciones predefinidas. "
                "Devuelve saldo anterior, cantidad ingresada, saldo actual y el movimiento creado.",
)
def recargar(
    payload: MonederoIngresoCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> MonederoRecargaResponse:
    result = monedero_service.ingresar(db, current_user.id, payload.cantidad)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return result


@router.get(
    "/movimientos",
    response_model=list[MovimientoMonederoRead],
    summary="Histórico de movimientos del monedero (RF-47)",
    description="Devuelve los movimientos del monedero del usuario autenticado "
                "ordenados del más reciente al más antiguo. Soporta paginación con `limite` y `offset`.",
)
def movimientos(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MovimientoMonederoRead]:
    return monedero_service.listar_movimientos(db, current_user.id, limite, offset)
