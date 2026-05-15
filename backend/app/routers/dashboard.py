"""Router para los endpoints del dashboard del usuario autenticado."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.usuario import Usuario
from app.schemas.dashboard import DashboardKPIs
from app.services.metricas_service import obtener_kpis_dashboard

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
