"""
Entorno de ejecución de migraciones Alembic para QuantVisionGC.

Configura la conexión a la base de datos leyendo la URL desde `settings`
(que a su vez la lee del .env del proyecto) y apunta `target_metadata` a la
Base declarativa de SQLAlchemy para que el autogenerate detecte los modelos.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Añadir backend/ al sys.path para que "from app.xxx import yyy" funcione
# cuando Alembic se ejecuta desde la carpeta backend/.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

# Importar los módulos de modelos para que Alembic los registre en la metadata
# y los detecte al generar migraciones con --autogenerate.
from app.models import (  # noqa: F401
    usuario,
    estrategia,
    resultado_estrategia,
    metrica_estrategia,
    contratacion,
    movimiento_monedero,
)

# ---------------------------------------------------------------------------
# Configuración estándar de Alembic
# ---------------------------------------------------------------------------
config = context.config

# Inyectar la URL desde settings antes de que Alembic configure el engine.
# Esto sustituye al valor sqlalchemy.url comentado en alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configurar el sistema de logging usando la sección [loggers] del alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de la Base declarativa: Alembic la usa en autogenerate para
# comparar el estado actual de los modelos con el esquema real de la BBDD.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migraciones en modo OFFLINE (sin conexión real a la BBDD)
# Genera el SQL de las migraciones en un archivo en lugar de ejecutarlo.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:   
    """Ejecuta las migraciones en modo offline (genera SQL sin conectar)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Migraciones en modo ONLINE (conexión real a la BBDD)
# Aplica las migraciones directamente contra PostgreSQL.
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo online (conectando a la BBDD)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
