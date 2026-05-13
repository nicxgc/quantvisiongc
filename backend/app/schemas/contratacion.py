from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.models.contratacion import EstadoContratacion


class ContratacionBase(BaseModel):
    id_estrategia: int


class ContratacionCreate(ContratacionBase):
    pass


class ContratacionUpdate(BaseModel):
    # Vacío a propósito: la cancelación se hace por endpoint dedicado
    # (PATCH /contrataciones/{id}/cancelar), no por PATCH genérico.
    pass


class ContratacionRead(ContratacionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_usuario: int
    monto_invertido: Decimal
    fecha_contratacion: datetime
    fecha_cancelacion: datetime | None
    estado: EstadoContratacion
