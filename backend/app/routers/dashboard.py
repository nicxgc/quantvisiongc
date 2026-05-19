"""Router para los endpoints del dashboard del usuario autenticado."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.dashboard import AccionReciente, DashboardKPIs
from app.services.metricas_service import obtener_actividad_reciente, obtener_kpis_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/kpis",
    response_model=DashboardKPIs,
    summary="KPIs agregados del dashboard del usuario autenticado",
    description=(
        "Devuelve los KPIs agregados del propio usuario: saldo del "
        "monedero, total invertido, valor actual de la cartera, "
        "P&L absoluto, rentabilidad total y número de contrataciones "
        "activas."
    ),
)
def obtener_kpis(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> DashboardKPIs:
    return obtener_kpis_dashboard(db, usuario_id=current_user.id)


@router.get(
    "/actividad-reciente",
    response_model=list[AccionReciente],
    summary="Actividad reciente del usuario (RF-27)",
    description=(
        "Devuelve los últimos N eventos de contratación y cancelación del usuario, "
        "ordenados del más reciente al más antiguo. "
        "Usa `limite` (1–50, defecto 10) para controlar cuántos eventos se devuelven."
    ),
)
def actividad_reciente(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    limite: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[AccionReciente]:
    return obtener_actividad_reciente(db, current_user.id, limite)
