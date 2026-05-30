"""
Punto de entrada principal de la API QuantVisionGC.

Inicializa la aplicación FastAPI, registra los middlewares globales (CORS)
e incluye los routers de cada módulo funcional.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.error_handlers import generic_exception_handler, value_error_handler
from app.core.limiter import limiter
from app.routers import admin_ingesta, auth, contrataciones, dashboard, estrategias, health, monedero

app = FastAPI(
    title="QuantVisionGC API",
    version="0.1.0",
    description="API REST del TFG QuantVisionGC",

)

app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS: solo se permite el origen del frontend en desarrollo local.
# En producción esta lista debe revisarse y restringirse al dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Demasiadas peticiones. Por favor, espera unos momentos antes "
                f"de volver a intentarlo. (Límite alcanzado: {exc.detail})"
            )
        },
    )

# Registro de routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(estrategias.router, prefix="/api/v1")
app.include_router(contrataciones.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(monedero.router, prefix="/api/v1")
app.include_router(admin_ingesta.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    """Endpoint raíz con información básica de la API."""
    return {
        "name": "QuantVisionGC API",
        "version": "0.1.0",
        "docs": "/docs",
    }
