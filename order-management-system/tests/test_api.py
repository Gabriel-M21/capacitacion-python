"""Tests de integración de la API - Módulo 9."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from order_management.api.routers.orders import _sequence


@pytest.fixture(autouse=True)
def reset_sequence() -> Generator[None, None, None]:
    _sequence[0] = 0
    yield
    _sequence[0] = 0


ORDER_PAYLOAD = {
    "customer": {
        "name": "Juan Pérez",
        "email": "juan.perez@example.com",
        "phone": "+52 55 1234 5678",
    },
    "items": [
        {"product_name": "Laptop Dell XPS 15", "quantity": 1, "unit_price": 1299.99},
        {"product_name": "Mouse Logitech", "quantity": 2, "unit_price": 29.99},
    ],
    "notes": "Entrega urgente",
}


# ---------------------------------------------------------------------------
# Auth — estos tests SÍ necesitan pasar por el endpoint real de login
# ---------------------------------------------------------------------------


def test_login_valid_credentials(client: TestClient) -> None:
    # Quitamos el override de get_current_user solo para este test
    from order_management.api.dependencies import get_current_user
    from order_management.api.main import app

    app.dependency_overrides.pop(get_current_user, None)

    response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "admin123"},
    )

    # Restaurar override
    app.dependency_overrides[get_current_user] = lambda: None

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient) -> None:
    from order_management.api.dependencies import get_current_user
    from order_management.api.main import app

    app.dependency_overrides.pop(get_current_user, None)

    response = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_orders_require_auth(db_session) -> None:
    """Sin override de auth, los endpoints deben devolver 401."""
    from order_management.api.dependencies import get_db
    from order_management.api.main import app

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: (yield db_session)
    with TestClient(app) as c:
        response = c.get("/orders")
    app.dependency_overrides.clear()
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------


def test_create_order(client: TestClient, auth_headers: dict) -> None:
    response = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["customer"]["name"] == "Juan Pérez"
    assert len(body["items"]) == 2
    assert body["status"] == "pending"
    assert float(body["total"]) == pytest.approx(1359.97, rel=1e-2)


def test_create_order_invalid_payload(client: TestClient, auth_headers: dict) -> None:
    response = client.post(
        "/orders",
        json={"customer": {"name": "", "email": "bad-email"}, "items": []},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------------


def test_list_orders_returns_created(client: TestClient, auth_headers: dict) -> None:
    client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    response = client.get("/orders", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


# ---------------------------------------------------------------------------
# GET /orders/{order_id}
# ---------------------------------------------------------------------------


def test_get_order_by_id(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    order_id = create.json()["order_id"]
    response = client.get(f"/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_get_order_not_found(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/orders/ORD-99999", headers=auth_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /orders/{order_id}/status
# ---------------------------------------------------------------------------


def test_update_status_valid(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    order_id = create.json()["order_id"]
    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "confirmed"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_update_status_invalid_transition(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    order_id = create.json()["order_id"]
    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_status_unknown_status(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    order_id = create.json()["order_id"]
    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "inventado"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /orders/{order_id}
# ---------------------------------------------------------------------------


def test_delete_order(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/orders", json=ORDER_PAYLOAD, headers=auth_headers)
    order_id = create.json()["order_id"]
    response = client.delete(f"/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get(f"/orders/{order_id}", headers=auth_headers).status_code == 404


def test_delete_order_not_found(client: TestClient, auth_headers: dict) -> None:
    response = client.delete("/orders/ORD-99999", headers=auth_headers)
    assert response.status_code == 404
