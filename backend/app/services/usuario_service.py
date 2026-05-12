"""Lógica de negocio relacionada con la entidad Usuario."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import UsuarioCreate


def create_usuario(db: Session, data: UsuarioCreate) -> Usuario:
    """Registra un nuevo usuario hashando su contraseña. Lanza ValueError si el correo ya existe."""
    user = Usuario(
        nombre_completo=data.nombre_completo,
        correo=data.correo,
        password_hash=hash_password(data.password),
        rol=RolUsuario.USER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("El correo ya está registrado")
    db.refresh(user)
    return user


def authenticate_usuario(db: Session, correo: str, password: str) -> Usuario | None:
    """Devuelve el Usuario si las credenciales son válidas, o None en caso contrario."""
    user = db.query(Usuario).filter(Usuario.correo == correo).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
