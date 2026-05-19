"""Schemas Pydantic v2 para la entidad Usuario."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.usuario import RolUsuario


class UsuarioBase(BaseModel):
    """Campos compartidos presentes en todas las operaciones de Usuario."""

    model_config = ConfigDict(str_strip_whitespace=True)

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

    @field_validator("password")
    @classmethod
    def password_debe_tener_letra_y_digito(cls, v: str) -> str:
        """Exige al menos una letra y un dígito en la contraseña."""
        if not any(c.isalpha() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra.")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número.")
        return v


class UsuarioUpdate(BaseModel):
    """Payload para actualizar parcialmente un usuario (PATCH). Solo nombre_completo es modificable por esta vía."""

    model_config = ConfigDict(str_strip_whitespace=True)

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
    saldo_monedero: Decimal = Field(..., description="Saldo disponible en el monedero virtual del usuario.")
    activa: bool = Field(..., description="False indica que la cuenta ha sido eliminada (soft delete).")


class LogoutResponse(BaseModel):
    """Respuesta del endpoint de cierre de sesión (RF-04)."""

    message: str = Field(..., description="Confirmación de cierre de sesión.")
