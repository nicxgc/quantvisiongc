"""Schemas Pydantic v2 para la entidad Usuario."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import RolUsuario


class UsuarioBase(BaseModel):
    """Campos compartidos presentes en todas las operaciones de Usuario."""

    nombre_completo: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nombre y apellidos del usuario.",
    )
    correo: EmailStr = Field(
        ...,
        description="Dirección de correo electrónico. Debe ser única en el sistema.",
    )


class UsuarioCreate(UsuarioBase):
    """Payload para registrar un nuevo usuario. La contraseña se recibe en claro y se hashea en el servicio."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Contraseña en texto plano. Mínimo 8 caracteres.",
    )


class UsuarioUpdate(BaseModel):
    """Payload para actualizar parcialmente un usuario (PATCH). Solo nombre_completo es modificable por esta vía."""

    nombre_completo: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Nuevo nombre completo del usuario.",
    )


class UsuarioRead(UsuarioBase):
    """Representación pública de un usuario. Nunca incluye password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador único del usuario.")
    rol: RolUsuario = Field(..., description="Rol del usuario en el sistema: 'admin' o 'user'.")
    fecha_registro: datetime = Field(..., description="Fecha y hora de registro con timezone.")
