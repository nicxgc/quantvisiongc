"""
Configuración de la capa de acceso a datos con SQLAlchemy (modo síncrono).

Expone:
- `engine`        : conexión al motor de base de datos PostgreSQL.
- `SessionLocal`  : fábrica de sesiones SQLAlchemy.
- `Base`          : clase base declarativa para los modelos ORM.
- `get_db()`      : dependencia de FastAPI que gestiona el ciclo de vida
                    de una sesión por petición HTTP.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

# Motor de base de datos.
# pool_pre_ping=True comprueba la conexión antes de cada uso para recuperarse
# automáticamente de cortes de red o reinicios del servidor de BBDD.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Fábrica de sesiones: autocommit y autoflush desactivados para que el
# control de transacciones sea explícito en cada endpoint.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base de la que heredarán todos los modelos ORM del proyecto.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI que proporciona una sesión de base de datos.

    Abre una sesión al inicio de la petición y la cierra siempre en el bloque
    finally, tanto si la petición tuvo éxito como si lanzó una excepción.

    Uso en un endpoint::

        @router.get("/ejemplo")
        def ejemplo(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
