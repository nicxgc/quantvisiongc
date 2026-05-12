"""Router de autenticación: registro de usuarios, login y perfil propio."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioRead
from app.services.usuario_service import authenticate_usuario, create_usuario

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/users/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def register(
    data: UsuarioCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Registra un nuevo usuario con rol 'user'. El correo debe ser único."""
    try:
        return create_usuario(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
