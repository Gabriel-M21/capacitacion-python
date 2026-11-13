"""
Engine y sesión SQLAlchemy - Módulo 8: Acceso a datos y ORM
Centraliza la configuración de la conexión a la base de datos.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# URL por defecto: SQLite local para desarrollo
# En producción se sobreescribe con una variable de entorno
DEFAULT_DATABASE_URL = "sqlite:///order_management.db"


def build_engine(database_url: str = DEFAULT_DATABASE_URL, **kwargs: Any) -> Engine:
    """
    Crea y configura el engine de SQLAlchemy.

    Para SQLite activa las foreign keys (desactivadas por defecto).

    Args:
        database_url: URL de conexión (sqlite / postgresql / mssql)
        **kwargs: Opciones adicionales para create_engine

    Returns:
        Engine configurado
    """
    engine = create_engine(database_url, **kwargs)

    # SQLite no activa FK por defecto; lo forzamos en cada conexión
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn: Any, _: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Engine y fábrica de sesiones para uso general
engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """
    Generador de sesiones para usar con 'with' o como dependencia en FastAPI.

    Example:
        with get_session() as session:
            session.add(model)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_in_memory_session() -> Generator[Session, None, None]:
    """
    Sesión con SQLite en memoria para pruebas.
    Crea las tablas automáticamente al iniciarse.

    Example:
        with get_in_memory_session() as session:
            # tablas creadas automáticamente
            session.add(model)
    """
    from order_management.infrastructure.db import models  # noqa: F401
    from order_management.infrastructure.db.base import Base

    test_engine = build_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    session = TestSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        Base.metadata.drop_all(test_engine)
