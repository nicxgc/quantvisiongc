"""Manejadores globales de excepciones de la aplicación.

Centralizan la conversión de excepciones de dominio a respuestas HTTP
para mantener los routers limpios y la respuesta de errores consistente
en toda la API.
"""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Traduce ValueError (excepción de dominio para señalar conflicto
    de estado) en una respuesta HTTP 409 Conflict.

    La convención del proyecto es que los servicios sean HTTP-agnósticos
    y lancen ValueError cuando detecten un conflicto (ej. doble
    contratación activa, email ya registrado, cancelación de una
    contratación ya cancelada). Este handler hace la traducción.
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Captura cualquier excepción no manejada y devuelve 500 Internal
    Server Error con un mensaje genérico (no expone trazas internas al
    cliente). El detalle completo queda registrado en el log del servidor
    para que el desarrollador pueda diagnosticar.
    """
    logger.exception(
        "Excepción no manejada en %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."},
    )
