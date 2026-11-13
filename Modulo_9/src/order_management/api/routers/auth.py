"""Router de autenticación - Módulo 9."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from order_management.api.dependencies import get_db
from order_management.api.security.jwt import create_access_token
from order_management.api.security.users import authenticate_user

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtener token de acceso",
    description=(
        "Autentica con email y contraseña y devuelve un JWT.\n\n"
        "**Credenciales de prueba:**\n"
        "- admin@example.com / admin123\n"
        "- user@example.com / user123"
    ),
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Autentica un usuario y devuelve un token JWT."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=token)
