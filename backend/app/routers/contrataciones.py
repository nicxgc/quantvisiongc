"""Router HTTP para el módulo de contrataciones."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.contratacion import ContratacionCreate, ContratacionRead
from app.services import contratacion_service

router = APIRouter(prefix="/contrataciones", tags=["contrataciones"])


@router.get(
    "/mis-contrataciones",
    response_model=List[ContratacionRead],
    summary="Listar mis contrataciones",
)
def mis_contrataciones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> List[ContratacionRead]:
    return contratacion_service.listar_contrataciones_usuario(db, current_user.id)


@router.post(
    "",
    response_model=ContratacionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Contratar una estrategia",
)
def contratar(
    datos: ContratacionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ContratacionRead:
    try:
        resultado = contratacion_service.contratar_estrategia(db, current_user.id, datos)
    except ValueError as e:
        codigo = str(e)
        if codigo == "contratacion_activa_existente":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya tienes una contratación activa sobre esta estrategia",
            )
        if codigo == "saldo_insuficiente":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Saldo insuficiente para contratar esta estrategia",
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=codigo)
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada o no disponible",
        )
    return resultado


@router.patch(
    "/{id_contratacion}/cancelar",
    response_model=ContratacionRead,
    summary="Cancelar una contratación",
)
def cancelar(
    id_contratacion: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ContratacionRead:
    try:
        resultado = contratacion_service.cancelar_contratacion(
            db, id_contratacion, current_user.id
        )
    except ValueError as e:
        if str(e) == "contratacion_ya_cancelada":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta contratación ya está cancelada",
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contratación no encontrada",
        )
    return resultado
