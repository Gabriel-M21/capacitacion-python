"""
Utilidades JWT - Módulo 9: APIs web con FastAPI
Crea y verifica tokens de acceso.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt  # type: ignore[import-untyped]

# En producción estas variables vienen de variables de entorno
SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Crea un JWT firmado con los datos proporcionados.

    Args:
        data: Payload del token (ej. {"sub": "usuario@email.com"})
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT como string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[no-any-return]


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
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore[no-any-return]


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
