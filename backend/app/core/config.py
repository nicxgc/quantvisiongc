"""
Configuración centralizada de la aplicación QuantVisionGC.

Usa pydantic-settings para leer variables de entorno desde el archivo .env
situado en la raíz del proyecto. Todas las variables de configuración se
exponen a través del singleton `settings`.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta a la raíz del proyecto (tres niveles por encima de este archivo:
# app/core/ -> app/ -> backend/ -> raíz/)
_ROOT_DIR: Path = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Ajustes globales de la aplicación leídos desde variables de entorno.

    Los valores por defecto cubren un entorno de desarrollo local típico.
    En producción deben sobreescribirse mediante el archivo .env o variables
    de entorno del sistema.
    """

    model_config = SettingsConfigDict(
        env_file=_ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Base de datos ---
    DATABASE_URL: str

    # --- Seguridad / JWT ---
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Servidor ---
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # --- Entorno ---
    ENVIRONMENT: str = "development"


# Instancia singleton; el resto de módulos importan este objeto directamente.
settings = Settings()


# ---------------------------------------------------------------------------
# Constantes de negocio (NO son variables de entorno, no van dentro de Settings)
# ---------------------------------------------------------------------------
from decimal import Decimal  # noqa: E402

# Denominaciones válidas para la recarga del monedero virtual (RF-46).
CANTIDADES_RECARGA_PERMITIDAS: tuple[Decimal, ...] = (
    Decimal("50.00"),
    Decimal("100.00"),
    Decimal("250.00"),
    Decimal("500.00"),
    Decimal("1000.00"),
    Decimal("5000.00"),
)
