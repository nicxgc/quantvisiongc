"""
Router de comprobación del estado del servicio (health check).

Proporciona un endpoint que verifica tanto que el servidor está activo como
que la base de datos es accesible. Útil para orquestadores de contenedores
(Docker, Kubernetes) y para depuración durante el desarrollo.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Comprueba que la API y la base de datos están operativas.

    Ejecuta una consulta mínima (`SELECT 1`) contra PostgreSQL. Si la consulta
    tiene éxito devuelve estado 200; si falla devuelve 503 para que los
    healthchecks externos marquen el servicio como no disponible.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ok", "database": "connected"}
