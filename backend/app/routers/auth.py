"""Router de autenticación: registro de usuarios, login y perfil propio."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token
from app.models.usuario import Usuario
from app.schemas.usuario import LogoutResponse, UsuarioCreate, UsuarioRead
from app.services.usuario_service import authenticate_usuario, create_usuario, eliminar_usuario, listar_usuarios

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/users/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def register(
    data: UsuarioCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Registra un nuevo usuario con rol 'user'. El correo debe ser único."""
    return create_usuario(db, data)


@router.post("/auth/login")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Autentica al usuario y devuelve un JWT Bearer. El campo 'username' contiene el correo."""
    user = authenticate_usuario(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/users/me", response_model=UsuarioRead)
def me(
    current: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Devuelve el perfil del usuario autenticado extraído del JWT."""
    return current


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    current: Annotated[Usuario, Depends(get_current_user)],
) -> LogoutResponse:
    """Cierra la sesión del usuario autenticado (RF-04).

    El backend es stateless (JWT puro): el token no se invalida en servidor.
    La invalidación efectiva la realiza el frontend descartando el token de
    su almacenamiento. El endpoint confirma que las credenciales eran válidas.
    """
    return LogoutResponse(message="Sesión cerrada correctamente.")


@router.get("/users", response_model=list[UsuarioRead], dependencies=[Depends(require_admin)])
def listar_todos_usuarios(
    db: Annotated[Session, Depends(get_db)],
) -> list[UsuarioRead]:
    """Lista todos los usuarios registrados ordenados por fecha de registro (RF-06). Solo admin."""
    return listar_usuarios(db)


@router.delete("/users/{id_usuario}", response_model=UsuarioRead, status_code=status.HTTP_200_OK)
def eliminar_usuario_endpoint(
    id_usuario: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> Usuario:
    """Elimina (soft delete) la cuenta de un usuario (RF-07). Solo admin.

    Cancela todas sus contrataciones activas y devuelve el monto_invertido
    al saldo_monedero del usuario antes de marcar activa=False.
    """
    usuario = eliminar_usuario(db, id_usuario, current_user.id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return usuario
