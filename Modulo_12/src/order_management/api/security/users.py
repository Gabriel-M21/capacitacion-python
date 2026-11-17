"""
Gestión de usuarios - Módulo 9: APIs web con FastAPI
Lee y escribe usuarios en la tabla 'users' de SQLite.
"""

import bcrypt
from sqlalchemy.orm import Session

from order_management.infrastructure.db.models import UserModel


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_user(db: Session, email: str) -> UserModel | None:
    """Busca un usuario por email en la DB."""
    return db.query(UserModel).filter_by(email=email).first()


def authenticate_user(db: Session, email: str, password: str) -> UserModel | None:
    """
    Autentica un usuario verificando email y contraseña contra la DB.

    Args:
        db: Sesión de base de datos
        email: Email del usuario
        password: Contraseña en texto plano

    Returns:
        UserModel o None si las credenciales son inválidas
    """
    user = get_user(db, email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str = "user",
    phone: str | None = None,
) -> UserModel:
    """
    Crea un usuario nuevo en la DB con contraseña hasheada.

    Args:
        db: Sesión de base de datos
        name: Nombre del usuario
        email: Email único
        password: Contraseña en texto plano (se hashea antes de guardar)
        role: Rol del usuario (default: 'user')
        phone: Teléfono opcional

    Returns:
        UserModel creado
    """
    user = UserModel(
        name=name,
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def seed_users(db: Session) -> None:
    """
    Crea los usuarios de prueba si no existen.
    Se llama al arrancar la aplicación.
    """
    defaults = [
        {
            "name": "Administrador",
            "email": "admin@example.com",
            "password": "admin123",
            "role": "admin",
        },
        {
            "name": "Usuario Normal",
            "email": "user@example.com",
            "password": "user123",
            "role": "user",
        },
    ]
    for data in defaults:
        if get_user(db, data["email"]) is None:
            create_user(
                db,
                name=data["name"],
                email=data["email"],
                password=data["password"],
                role=data["role"],
            )
    db.commit()
