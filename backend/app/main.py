"""
Punto de entrada principal de la API QuantVisionGC.

Inicializa la aplicación FastAPI, registra los middlewares globales (CORS)
e incluye los routers de cada módulo funcional.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, estrategias, health

app = FastAPI(
    title="QuantVisionGC API",
    version="0.1.0",
    description="API REST del TFG QuantVisionGC",
    
)

# CORS: solo se permite el origen del frontend en desarrollo local.
# En producción esta lista debe revisarse y restringirse al dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(estrategias.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    """Endpoint raíz con información básica de la API."""
    return {
        "name": "QuantVisionGC API",
        "version": "0.1.0",
        "docs": "/docs",
    }
