"""
Exportaciones públicas del paquete de modelos ORM.

Importar todos los modelos aquí garantiza que SQLAlchemy los registre en la
metadata de la Base antes de que Alembic genere migraciones con --autogenerate.
"""

from app.models.contratacion import Contratacion, EstadoContratacion
from app.models.estrategia import Estrategia, EstadoEstrategia
from app.models.resultado_estrategia import ResultadoEstrategia
from app.models.usuario import Usuario, RolUsuario

__all__ = [
    "Usuario",
    "RolUsuario",
    "Estrategia",
    "EstadoEstrategia",
    "ResultadoEstrategia",
    "Contratacion",
    "EstadoContratacion",
]
