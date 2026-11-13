"""
Dependencias de FastAPI - Módulo 9: APIs web con FastAPI
"""

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from order_management.api.security.jwt import verify_token
from order_management.api.security.users import get_user
from order_management.infrastructure.db.models import UserModel
from order_management.infrastructure.db.session import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    """Provee una sesión de base de datos por request."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """Verifica el JWT y devuelve el UserModel autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = verify_token(token)
    if email is None:
        raise credentials_exception

    user = get_user(db, email)
    if user is None:
        raise credentials_exception

    return user
