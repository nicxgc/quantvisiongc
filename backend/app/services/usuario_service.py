"""Lógica de negocio relacionada con la entidad Usuario."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import UsuarioCreate
from app.services.contratacion_service import cancelar_contrataciones_de_usuario


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


def listar_usuarios(db: Session) -> list[Usuario]:
    """Devuelve todos los usuarios ordenados por fecha_registro descendente (RF-06)."""
    return list(db.scalars(select(Usuario).order_by(Usuario.fecha_registro.desc())).all())


def authenticate_usuario(db: Session, correo: str, password: str) -> Usuario | None:
    """Devuelve el Usuario si las credenciales son válidas, o None en caso contrario.

    Devuelve None también si el usuario tiene activa=False para no filtrar
    la existencia de la cuenta a posibles atacantes (mismo mensaje 401 genérico).
    """
    user = db.query(Usuario).filter(Usuario.correo == correo).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.activa:
        return None
    return user


def eliminar_usuario(db: Session, id_usuario: int, id_admin: int) -> Usuario | None:
    """Soft delete de un usuario: marca activa=False y cancela sus contrataciones activas.

    La devolución de monto_invertido al saldo_monedero de cada contratación cancelada
    se hace dentro de cancelar_contrataciones_de_usuario (sin commit intermedio).
    Toda la operación es atómica: un único commit al final.

    Returns:
        Usuario actualizado, o None si no existe.

    Raises:
        - ValueError("Un administrador no puede eliminar su propia cuenta") si id_usuario == id_admin.
        - ValueError("El usuario ya estaba eliminado") si usuario.activa is False.
    """
    if id_usuario == id_admin:
        raise ValueError("Un administrador no puede eliminar su propia cuenta")

    usuario = db.get(Usuario, id_usuario)
    if usuario is None:
        return None

    if not usuario.activa:
        raise ValueError("El usuario ya estaba eliminado")

    cancelar_contrataciones_de_usuario(db, id_usuario)
    usuario.activa = False

    db.commit()
    db.refresh(usuario)
    return usuario
