"""
Test integrador del sistema de órdenes - Proyecto Final
Prueba el flujo completo end-to-end:
  CreateOrderCommand
      → CreateOrderUseCase (UoW + EventBus + Presenter)
      → Order persistida en SQLite en memoria
      → Evento OrderCreated publicado y manejado
      → API FastAPI expone la orden
      → CLI puede consultar y modificar
      → Repositorio SQLAlchemy verifica persistencia

Capas involucradas en cada test:
  Dominio → Aplicación → Infraestructura → API
"""

from collections.abc import Generator
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from order_management.api.dependencies import get_current_user, get_db
from order_management.api.main import app
from order_management.api.routers.orders import _sequence
from order_management.api.security.jwt import create_access_token
from order_management.api.security.users import seed_users as _seed_fn
from order_management.application.dtos import CreateOrderCommand, OrderItemCommand
from order_management.application.event_bus import EventBus
from order_management.application.presenters import (
    ApiPresenter,
    AuditPresenter,
    CliPresenter,
    JsonPresenter,
)
from order_management.application.unit_of_work import InMemoryUnitOfWork
from order_management.application.use_cases.create_order import CreateOrderUseCase
from order_management.domain.events import OrderCreated, OrderStatusChanged
from order_management.domain.value_objects import OrderId, OrderStatus
from order_management.infrastructure.db import models  # noqa: F401
from order_management.infrastructure.db.base import Base
from order_management.infrastructure.db.models import UserModel
from order_management.infrastructure.db.repositories.order_repository import OrderRepository
from order_management.infrastructure.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork

_test_engine = create_engine(
    "sqlite:///test.db",
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(_test_engine)
_TestSession = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)

# Seed usuarios
_seed_db = _TestSession()
try:
    _seed_fn(_seed_db)
except Exception:
    _seed_db.rollback()
finally:
    _seed_db.close()

_MOCK_USER = UserModel(
    id=1,
    name="Administrador",
    email="admin@example.com",
    hashed_password="",
    role="admin",
)


# ---------------------------------------------------------------------------
# Fixtures compartidos
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_sequence() -> Generator[None, Any, None]:
    _sequence[0] = 0
    yield
    _sequence[0] = 0


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = _TestSession()
    yield db
    db.rollback()
    db.close()


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_current_user() -> Any:
        return _MOCK_USER

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(data={"sub": "admin@example.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


SAMPLE_COMMAND = CreateOrderCommand(
    customer_name="Juan Pérez",
    customer_email="juan.perez@example.com",
    customer_phone="+52 55 1234 5678",
    sequence_number=1,
    notes="Entrega urgente",
    items=[
        OrderItemCommand("Laptop Dell XPS 15", 1, Decimal("1299.99")),
        OrderItemCommand("Mouse Logitech MX Master", 2, Decimal("49.99")),
    ],
)

ORDER_API_PAYLOAD: dict[str, Any] = {
    "customer": {
        "name": "Juan Pérez",
        "email": "juan.perez@example.com",
        "phone": "+52 55 1234 5678",
    },
    "items": [
        {"product_name": "Laptop Dell XPS 15", "quantity": 1, "unit_price": 1299.99},
        {"product_name": "Mouse Logitech MX Master", "quantity": 2, "unit_price": 49.99},
    ],
    "notes": "Entrega urgente",
}


# ===========================================================================
# BLOQUE 1 — DOMINIO PURO (sin infraestructura)
# ===========================================================================


class TestDominioPuro:
    """Reglas de negocio del dominio sin ninguna dependencia externa."""

    def test_order_calcula_total_correctamente(self) -> None:
        from order_management.domain.entities import Customer, Order, OrderItem
        from order_management.domain.value_objects import Email, Money, OrderId

        customer = Customer("Test", Email("t@example.com"))
        items = [
            OrderItem("Laptop", 1, Money(Decimal("1299.99"), "USD")),
            OrderItem("Mouse", 2, Money(Decimal("49.99"), "USD")),
        ]
        order = Order(OrderId.generate(1), customer, items)
        assert order.total == Money(Decimal("1399.97"), "USD")

    def test_transiciones_de_estado_validas(self) -> None:
        assert OrderStatus.PENDING.can_transition_to(OrderStatus.CONFIRMED)
        assert OrderStatus.CONFIRMED.can_transition_to(OrderStatus.PROCESSING)
        assert OrderStatus.PROCESSING.can_transition_to(OrderStatus.SHIPPED)
        assert OrderStatus.SHIPPED.can_transition_to(OrderStatus.DELIVERED)

    def test_transiciones_invalidas_rechazadas(self) -> None:
        assert not OrderStatus.PENDING.can_transition_to(OrderStatus.DELIVERED)
        assert not OrderStatus.PENDING.can_transition_to(OrderStatus.SHIPPED)
        assert not OrderStatus.DELIVERED.can_transition_to(OrderStatus.CANCELLED)

    def test_eventos_de_dominio_son_inmutables(self) -> None:
        event = OrderCreated(order_id="ORD-001", total=Decimal("100"))
        with pytest.raises((AttributeError, TypeError)):
            event.order_id = "OTRO"  # type: ignore[misc]

    def test_order_id_formato_correcto(self) -> None:
        assert str(OrderId.generate(1)) == "ORD-00001"
        assert str(OrderId.generate(999)) == "ORD-00999"

    def test_order_sin_items_lanza_error(self) -> None:
        from order_management.domain.entities import Customer, Order
        from order_management.domain.value_objects import Email

        customer = Customer("Test", Email("t@example.com"))
        with pytest.raises(ValueError, match="al menos un item"):
            Order(OrderId.generate(1), customer, [])


# ===========================================================================
# BLOQUE 2 — CASO DE USO (capa de aplicación)
# ===========================================================================


class TestCasoDeUsoCreateOrder:
    """CreateOrderUseCase con UoW y EventBus — sin API ni HTTP."""

    def test_ejecuta_y_devuelve_resultado_json(
        self, uow: InMemoryUnitOfWork, bus: EventBus
    ) -> None:
        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter())
        result = uc.execute(SAMPLE_COMMAND)

        assert isinstance(result, dict)
        assert result["order_id"] == "ORD-00001"
        assert result["status"] == "pending"
        assert result["item_count"] == 2
        assert result["total"] == pytest.approx(1399.97, rel=1e-2)

    def test_ejecuta_y_devuelve_resultado_cli(self, uow: InMemoryUnitOfWork, bus: EventBus) -> None:
        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=CliPresenter())
        result = uc.execute(SAMPLE_COMMAND)
        assert isinstance(result, str)
        assert "ORD-00001" in result
        assert "Juan Pérez" in result

    def test_ejecuta_y_devuelve_resultado_api(self, uow: InMemoryUnitOfWork, bus: EventBus) -> None:
        from order_management.schemas.schemas import OrderOut

        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=ApiPresenter())
        result = uc.execute(SAMPLE_COMMAND)
        assert isinstance(result, OrderOut)
        assert result.order_id == "ORD-00001"

    def test_ejecuta_y_devuelve_resultado_auditoria(
        self, uow: InMemoryUnitOfWork, bus: EventBus
    ) -> None:
        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=AuditPresenter())
        result = uc.execute(SAMPLE_COMMAND)
        assert result["event"] == "ORDER_CREATED"
        assert result["order_id"] == "ORD-00001"

    def test_persiste_orden_en_uow(self, uow: InMemoryUnitOfWork, bus: EventBus) -> None:
        CreateOrderUseCase(uow=uow, event_bus=bus).execute(SAMPLE_COMMAND)
        orders = uow.orders.list_all()
        assert len(orders) == 1
        assert str(orders[0].order_id) == "ORD-00001"

    def test_commit_fue_llamado(self, uow: InMemoryUnitOfWork, bus: EventBus) -> None:
        CreateOrderUseCase(uow=uow, event_bus=bus).execute(SAMPLE_COMMAND)
        assert uow.was_committed is True

    def test_publica_evento_order_created(self, uow: InMemoryUnitOfWork) -> None:
        received: list[OrderCreated] = []
        bus = EventBus()
        bus.register(OrderCreated, received.append)

        CreateOrderUseCase(uow=uow, event_bus=bus).execute(SAMPLE_COMMAND)

        assert len(received) == 1
        assert received[0].order_id == "ORD-00001"
        assert received[0].customer_email == "juan.perez@example.com"
        assert received[0].total == pytest.approx(Decimal("1399.97"), rel=Decimal("0.01"))

    def test_multiples_handlers_se_ejecutan(self, uow: InMemoryUnitOfWork) -> None:
        notify_log: list[str] = []
        audit_log: list[str] = []
        bus = EventBus()
        bus.register(OrderCreated, lambda e: notify_log.append(e.order_id))
        bus.register(OrderCreated, lambda e: audit_log.append(f"AUDIT:{e.order_id}"))

        CreateOrderUseCase(uow=uow, event_bus=bus).execute(SAMPLE_COMMAND)

        assert notify_log == ["ORD-00001"]
        assert audit_log == ["AUDIT:ORD-00001"]

    def test_notificacion_fallida_no_rompe_flujo(self, uow: InMemoryUnitOfWork) -> None:
        bus = EventBus()
        bus.register(OrderCreated, lambda e: (_ for _ in ()).throw(Exception("Red caída")))

        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter())
        result = uc.execute(SAMPLE_COMMAND)

        assert result["order_id"] == "ORD-00001"
        assert len(uow.orders.list_all()) == 1

    def test_separacion_capas_sin_infraestructura(self) -> None:
        """El caso de uso no importa SQLAlchemy, FastAPI ni httpx."""
        import importlib
        import inspect

        module: ModuleType = importlib.import_module(
            "order_management.application.use_cases.create_order"
        )
        source: str = inspect.getsource(module)
        assert "sqlalchemy" not in source.lower()
        assert "fastapi" not in source.lower()
        assert "httpx" not in source.lower()


# ===========================================================================
# BLOQUE 3 — REPOSITORIO SQLAlchemy (infraestructura DB)
# ===========================================================================


class TestRepositorioSQLAlchemy:
    """OrderRepository con SQLite en memoria — prueba la capa de persistencia."""

    def test_save_y_get_by_order_id(self, db_session: Session) -> None:
        from order_management.domain.entities import Customer, Order, OrderItem
        from order_management.domain.value_objects import Email, Money, OrderId

        order = Order(
            order_id=OrderId.generate(1),
            customer=Customer("Juan", Email("juan@example.com")),
            items=[OrderItem("Laptop", 1, Money(Decimal("1299.99"), "USD"))],
        )
        repo = OrderRepository(db_session)
        repo.save(order)
        db_session.commit()

        recovered = repo.get_by_order_id("ORD-00001")
        assert recovered.customer.name == "Juan"
        assert recovered.total.amount == Decimal("1299.99")

    def test_update_status(self, db_session: Session) -> None:
        from order_management.domain.entities import Customer, Order, OrderItem
        from order_management.domain.value_objects import Email, Money, OrderId

        order = Order(
            order_id=OrderId.generate(2),
            customer=Customer("María", Email("maria@example.com")),
            items=[OrderItem("Mouse", 1, Money(Decimal("99.99"), "USD"))],
        )
        repo = OrderRepository(db_session)
        repo.save(order)
        db_session.commit()

        updated = repo.update_status("ORD-00002", OrderStatus.CONFIRMED)
        db_session.commit()
        assert updated.status == OrderStatus.CONFIRMED

    def test_delete(self, db_session: Session) -> None:
        from order_management.domain.entities import Customer, Order, OrderItem
        from order_management.domain.value_objects import Email, Money, OrderId
        from order_management.infrastructure.db.repositories.order_repository import (
            OrderNotFoundError,
        )

        order = Order(
            order_id=OrderId.generate(3),
            customer=Customer("Carlos", Email("carlos@example.com")),
            items=[OrderItem("SSD", 1, Money(Decimal("89.99"), "USD"))],
        )
        repo = OrderRepository(db_session)
        repo.save(order)
        db_session.commit()

        repo.delete("ORD-00003")
        db_session.commit()

        with pytest.raises(OrderNotFoundError):
            repo.get_by_order_id("ORD-00003")

    def test_uow_sqlalchemy_commit_y_rollback(self) -> None:
        from order_management.domain.entities import Customer, Order, OrderItem
        from order_management.domain.value_objects import Email, Money, OrderId

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        order = Order(
            order_id=OrderId.generate(10),
            customer=Customer("Test UoW", Email("uow@example.com")),
            items=[OrderItem("Producto", 1, Money(Decimal("50.00"), "USD"))],
        )

        # Commit exitoso
        with SqlAlchemyUnitOfWork(Session) as uow:
            assert uow.orders is not None  # fix: orders puede ser None antes de __enter__
            uow.orders.save(order)
            uow.add_event(OrderCreated(order_id="ORD-00010"))
            uow.commit()

        events = uow.collect_events()
        assert len(events) == 1
        assert events[0].order_id == "ORD-00010"  # type: ignore[attr-defined]


# ===========================================================================
# BLOQUE 4 — API FastAPI (capa de controladores)
# ===========================================================================


class TestApiFastAPI:
    """Endpoints REST con SQLite en memoria inyectado via dependency override."""

    def test_health_check(self, api_client: TestClient) -> None:
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_crear_orden(self, api_client: TestClient, auth_headers: dict[str, str]) -> None:
        resp = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["customer"]["name"] == "Juan Pérez"
        assert data["status"] == "pending"
        assert float(data["total"]) == pytest.approx(1399.97, rel=1e-2)

    def test_listar_ordenes(self, api_client: TestClient, auth_headers: dict[str, str]) -> None:
        api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        resp = api_client.get("/orders", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_obtener_orden_por_id(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        create = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        order_id = create.json()["order_id"]

        resp = api_client.get(f"/orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["order_id"] == order_id

    def test_orden_no_encontrada(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        resp = api_client.get("/orders/ORD-99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_cambiar_estado_valido(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        create = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        order_id = create.json()["order_id"]

        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_cambiar_estado_invalido(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        create = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        order_id = create.json()["order_id"]

        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "delivered"},  # pending → delivered no es válido
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_eliminar_orden(self, api_client: TestClient, auth_headers: dict[str, str]) -> None:
        create = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        order_id = create.json()["order_id"]

        resp = api_client.delete(f"/orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = api_client.get(f"/orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_sin_autenticacion_devuelve_401(self, db_session: Session) -> None:
        """Sin override de auth, el endpoint debe devolver 401."""

        def override_get_db() -> Generator[Session, None, None]:
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            resp = c.get("/orders")
        app.dependency_overrides.clear()
        assert resp.status_code == 401

    def test_payload_invalido_devuelve_422(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        resp = api_client.post(
            "/orders",
            json={"customer": {"name": "", "email": "mal"}, "items": []},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# BLOQUE 5 — FLUJO COMPLETO END-TO-END
# ===========================================================================


class TestFlujoCompletoE2E:
    """
    Prueba el sistema completo: desde el comando hasta la API,
    pasando por todas las capas.
    """

    def test_ciclo_vida_completo_orden(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Crea una orden → confirma → envía → entrega."""
        # 1. Crear
        resp = api_client.post("/orders", json=ORDER_API_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        order_id = resp.json()["order_id"]
        assert resp.json()["status"] == "pending"

        # 2. Confirmar
        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

        # 3. Processing
        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "processing"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # 4. Shipped
        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "shipped"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # 5. Delivered
        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "delivered"

        # 6. Verificar que ya no se puede cambiar
        resp = api_client.patch(
            f"/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_eventos_publicados_durante_ciclo_de_vida(self, uow: InMemoryUnitOfWork) -> None:
        """UoW + EventBus: verifica que los eventos correctos se publican."""
        events_received: list[Any] = []
        bus = EventBus()
        bus.register(OrderCreated, events_received.append)
        bus.register(OrderStatusChanged, events_received.append)

        # Crear orden
        CreateOrderUseCase(uow=uow, event_bus=bus).execute(SAMPLE_COMMAND)
        assert len(events_received) == 1
        assert isinstance(events_received[0], OrderCreated)
        assert events_received[0].order_id == "ORD-00001"

        # Cambiar estado manualmente y publicar evento
        orders = uow.orders.list_all()
        order = orders[0]
        old_status = order.status.value
        order.change_status(OrderStatus.CONFIRMED)
        bus.publish(
            OrderStatusChanged(
                order_id=str(order.order_id),
                old_status=old_status,
                new_status=order.status.value,
            )
        )

        assert len(events_received) == 2
        assert isinstance(events_received[1], OrderStatusChanged)
        assert events_received[1].new_status == "confirmed"

    def test_multiples_ordenes_misma_sesion(
        self, api_client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Crear 3 órdenes y listarlas todas."""
        for _i in range(3):
            payload: dict[str, Any] = dict(ORDER_API_PAYLOAD)
            resp = api_client.post("/orders", json=payload, headers=auth_headers)
            assert resp.status_code == 201

        resp = api_client.get("/orders", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_caso_uso_con_sqlalchemy_uow_e2e(self) -> None:
        """Flujo completo usando SqlAlchemyUnitOfWork con SQLite en memoria."""
        from order_management.domain.events import OrderCreated as OC

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        events: list[Any] = []
        bus = EventBus()
        bus.register(OC, events.append)

        uow = SqlAlchemyUnitOfWork(Session)
        uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter())

        result = uc.execute(SAMPLE_COMMAND)

        assert result["order_id"] == "ORD-00001"
        assert result["status"] == "pending"
        assert len(events) == 1
        assert events[0].order_id == "ORD-00001"

        # Verificar persistencia real en SQLite
        with Session() as session:
            repo = OrderRepository(session)
            order = repo.get_by_order_id("ORD-00001")
            assert order.customer.name == "Juan Pérez"
            assert order.total.amount == pytest.approx(Decimal("1399.97"), rel=Decimal("0.01"))
