"""
Configuración central de pruebas - fixtures compartidos.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from order_management.api.dependencies import get_current_user, get_db
from order_management.api.main import app
from order_management.api.security.jwt import create_access_token
from order_management.api.security.users import seed_users
from order_management.infrastructure.db import models  # noqa: F401
from order_management.infrastructure.db.base import Base


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///test.db",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def SessionFactory(test_engine) -> sessionmaker:
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def seed(SessionFactory: sessionmaker) -> None:
    db = SessionFactory()
    try:
        seed_users(db)
    finally:
        db.close()


@pytest.fixture
def db_session(SessionFactory: sessionmaker) -> Session:
    db = SessionFactory()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """
    TestClient con AMBAS dependencias (get_db y get_current_user)
    apuntando al mismo engine en memoria.
    """
    from order_management.infrastructure.db.models import UserModel

    # Usuario admin simulado sin consultar la DB
    mock_user = UserModel(
        id=1,
        name="Administrador",
        email="admin@example.com",
        hashed_password="",
        role="admin",
    )

    def override_get_db():
        yield db_session

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(db_session: Session) -> dict[str, str]:
    """JWT generado directamente, sin pasar por el endpoint de login."""
    token = create_access_token(data={"sub": "admin@example.com"})
    return {"Authorization": f"Bearer {token}"}
