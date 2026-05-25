"""Router HTTP para el módulo de contrataciones."""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.contratacion import ContratacionCreate, ContratacionRead
from app.services import contratacion_service
from app.services.contratacion_service import BenchmarkNoContratableError

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
    description=(
        "Descuenta el precio de suscripción del saldo del monedero y crea "
        "una contratación activa. Solo se pueden contratar estrategias de tipo "
        "'estrategia_activa'; los benchmarks devuelven **400**. "
        "Devuelve **404** si la estrategia no existe o no está disponible, "
        "**409** si ya tienes una contratación activa sobre esa estrategia o "
        "si el saldo es insuficiente."
    ),
    responses={
        400: {"description": "La estrategia es un benchmark y no puede contratarse."},
        404: {"description": "Estrategia no encontrada o no disponible."},
        409: {"description": "Contratación activa existente o saldo insuficiente."},
    },
)
def contratar(
    datos: ContratacionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ContratacionRead:
    try:
        resultado = contratacion_service.contratar_estrategia(db, current_user.id, datos)
    except BenchmarkNoContratableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada o no disponible.",
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
    resultado = contratacion_service.cancelar_contratacion(
        db, id_contratacion, current_user.id
    )
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contratación no encontrada.",
        )
    return resultado
