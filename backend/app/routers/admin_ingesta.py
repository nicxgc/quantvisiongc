"""Router HTTP para la ingesta de paquetes de estrategias.

Expone el endpoint:

    POST /api/v1/admin/ingesta/paquete

Solo accesible con JWT de rol 'admin'.  Recibe un fichero ZIP (multipart
form-data) con los tres xlsx del paquete, valida y persiste los datos,
y devuelve una respuesta estructurada con el resumen o los errores.

Códigos HTTP
------------
200  Ingesta completada con éxito (summary en cuerpo).
400  Archivo inválido, ZIP mal formado, archivos faltantes en el ZIP,
     o errores de validación en los xlsx.
401  Sin token o token inválido.
403  Token válido pero el usuario no tiene rol 'admin'.
409  Paquete duplicado: ya existen estrategias con esos codigos en BD.
500  Error inesperado en la capa de persistencia (fallo de BD).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.limiter import limiter
from app.models.usuario import Usuario
from app.schemas.ingesta import (
    IngestaErrorSchema,
    IngestaResponseSchema,
    IngestaSummarySchema,
)
from app.services.ingesta.ingesta_service import ingestar_paquete

router = APIRouter(prefix="/admin", tags=["Admin · Ingesta"])

# Mapeo código de error → HTTP status.
# Los códigos no listados aquí devuelven 400 por defecto.
_CODIGO_A_HTTP: dict[str, int] = {
    "ZIP_INVALID":          400,
    "ZIP_INCOMPLETE":       400,
    "CONFLICT_DUPLICATE":   409,
    "DB_ERROR":             500,
}


def _to_schema(errores) -> list[IngestaErrorSchema]:
    """Convierte una lista de IngestaError (dataclasses) en schemas Pydantic."""
    return [IngestaErrorSchema.model_validate(vars(e)) for e in errores]


@router.post(
    "/ingesta/paquete",
    response_model=IngestaResponseSchema,
    status_code=200,
    summary="Ingestar paquete de estrategias",
    description=(
        "Recibe un ZIP con los tres xlsx del paquete "
        "(strategies.xlsx, metrics_summary.xlsx, equity_curves.xlsx), "
        "los valida y persiste los datos en BD. "
        "Requiere JWT con rol **admin**."
    ),
)
@limiter.limit("5/hour")
async def post_ingesta_paquete(
    request: Request,
    response: Response,
    archivo: Annotated[UploadFile, File(description="Fichero ZIP con los tres xlsx.")],
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[Usuario, Depends(require_admin)],
) -> IngestaResponseSchema:
    """Endpoint principal de ingesta de paquetes."""

    # ── Validar extensión del fichero ──────────────────────────────────────
    nombre = archivo.filename or "archivo_sin_nombre"
    if not nombre.lower().endswith(".zip"):
        response.status_code = 400
        return IngestaResponseSchema(
            status="error",
            errores=[
                IngestaErrorSchema(
                    archivo=nombre,
                    codigo="ZIP_INVALID",
                    mensaje=(
                        f"El archivo '{nombre}' no tiene extensión .zip. "
                        "Solo se aceptan ficheros ZIP."
                    ),
                )
            ],
        )

    zip_bytes = await archivo.read()

    # ── Llamar al servicio orquestador ─────────────────────────────────────
    summary_dict, errores = ingestar_paquete(zip_bytes, db)

    if summary_dict is not None:
        # Ingesta exitosa: puede haber warnings pero no errores bloqueantes
        return IngestaResponseSchema(
            status="ok",
            summary=IngestaSummarySchema(**summary_dict),
            errores=_to_schema(errores),
        )

    # Ingesta fallida: calcular el HTTP status más grave
    http_status = 400
    for err in errores:
        candidate = _CODIGO_A_HTTP.get(err.codigo, 400)
        if candidate > http_status:
            http_status = candidate

    response.status_code = http_status
    return IngestaResponseSchema(
        status="error",
        errores=_to_schema(errores),
    )
