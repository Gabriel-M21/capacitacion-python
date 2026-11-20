"""
Engine y sesión SQLAlchemy - actualizado en Módulo 19
Lee DATABASE_URL desde Settings en vez de tenerla hardcodeada.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from order_management.config.settings import get_settings


def build_engine(database_url: str | None = None, **kwargs: Any) -> Engine:
    """
    Crea y configura el engine de SQLAlchemy.

    Si no se pasa database_url, la lee desde Settings (variable de entorno
    DATABASE_URL o el valor por defecto sqlite:///order_management.db).

    Args:
        database_url: URL de conexión opcional (sobreescribe Settings)
        **kwargs:     Opciones adicionales para create_engine

    Returns:
        Engine configurado
    """
    settings = get_settings()
    url = database_url or settings.database_url

    engine = create_engine(url, echo=settings.db_echo, **kwargs)

    # SQLite no activa FK por defecto; lo forzamos en cada conexión
    if url.startswith("sqlite"):

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
