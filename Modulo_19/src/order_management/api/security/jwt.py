"""
Utilidades JWT - Módulo 9 / actualizado en Módulo 19
Lee SECRET_KEY y configuración desde Settings (pydantic-settings)
en vez de tenerlos hardcodeados.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from order_management.config.settings import get_settings


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Crea un JWT firmado con los datos proporcionados.

    Args:
        data:          Payload del token (ej. {"sub": "usuario@email.com"})
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT como string
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y verifica un JWT.

    Args:
        token: Token JWT a verificar

    Returns:
        Payload decodificado

    Raises:
        JWTError: Si el token es inválido o expiró
    """
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def verify_token(token: str) -> str | None:
    """
    Verifica un token y devuelve el subject (email del usuario).

    Args:
        token: Token JWT

    Returns:
        Email del usuario o None si el token es inválido
    """
    try:
        payload = decode_access_token(token)
        subject: str | None = payload.get("sub")
        return subject
    except JWTError:
        return None
