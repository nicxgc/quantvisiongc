"""
Punto de importación centralizado de la Base declarativa ORM.

Todos los modelos del proyecto deben importar `Base` desde aquí en lugar de
hacerlo directamente desde `app.core.database`, de modo que el árbol de
importaciones sea más limpio y los modelos no dependan de detalles internos
del módulo de base de datos.

Uso::

    from app.models.base import Base

    class MiModelo(Base):
        __tablename__ = "mi_tabla"
        ...
"""

from app.core.database import Base

__all__ = ["Base"]
