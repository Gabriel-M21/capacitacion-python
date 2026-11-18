"""
Pruebas de Arquitectura Limpia - Módulo 16
Cubre: eventos, UoW, EventBus, Presenters y caso de uso v2.
"""

from decimal import Decimal
from typing import Any

import pytest

from order_management.application.dtos import CreateOrderCommand, OrderItemCommand
from order_management.application.event_bus import EventBus
from order_management.application.presenters import (
    ApiPresenter,
    AuditPresenter,
    CliPresenter,
    JsonPresenter,
    OrderPresenterPort,
)
from order_management.application.unit_of_work import InMemoryUnitOfWork
from order_management.application.use_cases.create_order import CreateOrderUseCase
from order_management.domain.events import DomainEvent, OrderCreated, OrderStatusChanged

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_command() -> CreateOrderCommand:
    return CreateOrderCommand(
        customer_name="Juan Pérez",
        customer_email="juan.perez@example.com",
        sequence_number=1,
        notes="Entrega urgente",
        items=[
            OrderItemCommand("Laptop Dell XPS 15", 1, Decimal("1299.99")),
            OrderItemCommand("Mouse Logitech MX Master", 2, Decimal("49.99")),
        ],
    )


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def use_case(uow: InMemoryUnitOfWork, bus: EventBus) -> CreateOrderUseCase:
    return CreateOrderUseCase(uow=uow, event_bus=bus)


# ---------------------------------------------------------------------------
# 1. PRUEBAS DE EVENTOS DE DOMINIO
# ---------------------------------------------------------------------------


def test_evento_order_created_es_inmutable() -> None:
    """Los eventos de dominio son frozen dataclasses."""
    event = OrderCreated(
        order_id="ORD-00001",
        customer_email="juan@example.com",
        total=Decimal("1399.97"),
    )
    with pytest.raises((AttributeError, TypeError)):
        event.order_id = "OTRO"  # type: ignore[misc]


def test_evento_order_created_tiene_id_y_timestamp() -> None:
    """Todo evento tiene event_id único y occurred_at automático."""
    e1 = OrderCreated(order_id="ORD-001")
    e2 = OrderCreated(order_id="ORD-002")
    assert e1.event_id != e2.event_id
    assert e1.occurred_at is not None


def test_evento_es_instancia_de_domain_event() -> None:
    """Todos los eventos heredan de DomainEvent."""
    assert isinstance(OrderCreated(), DomainEvent)
    assert isinstance(OrderStatusChanged(), DomainEvent)


# ---------------------------------------------------------------------------
# 2. PRUEBAS DEL UNIT OF WORK
# ---------------------------------------------------------------------------


def test_uow_commit_marca_como_confirmado(uow: InMemoryUnitOfWork) -> None:
    with uow:
        uow.commit()
    assert uow.was_committed is True


def test_uow_rollback_en_excepcion(uow: InMemoryUnitOfWork) -> None:
    """Si hay excepción dentro del with, se hace rollback automático."""
    from order_management.domain.entities import Customer, Order, OrderItem
    from order_management.domain.value_objects import Email, Money, OrderId

    order = Order(
        order_id=OrderId.generate(1),
        customer=Customer("Test", Email("t@example.com")),
        items=[OrderItem("P", 1, Money(Decimal("10"), "USD"))],
    )

    try:
        with uow:
            uow.orders.save(order)
            raise ValueError("Fallo simulado")
    except ValueError:
        pass

    # Después del rollback el repositorio está vacío
    assert len(uow.orders.list_all()) == 0


def test_uow_acumula_y_devuelve_eventos(uow: InMemoryUnitOfWork) -> None:
    event = OrderCreated(order_id="ORD-001")
    with uow:
        uow.add_event(event)
        uow.commit()

    events = uow.collect_events()
    assert len(events) == 1
    assert events[0].order_id == "ORD-001"  # type: ignore[attr-defined]


def test_uow_collect_events_vacia_buffer(uow: InMemoryUnitOfWork) -> None:
    with uow:
        uow.add_event(OrderCreated(order_id="ORD-001"))
        uow.commit()

    uow.collect_events()  # primer collect
    assert uow.collect_events() == []  # segundo collect → vacío


# ---------------------------------------------------------------------------
# 3. PRUEBAS DEL EVENT BUS
# ---------------------------------------------------------------------------


def test_event_bus_llama_handler_registrado(bus: EventBus) -> None:
    received: list[OrderCreated] = []

    @bus.subscribe(OrderCreated)
    def handler(event: OrderCreated) -> None:
        received.append(event)

    event = OrderCreated(order_id="ORD-001", customer_email="juan@example.com")
    bus.publish(event)

    assert len(received) == 1
    assert received[0].order_id == "ORD-001"


def test_event_bus_multiples_handlers(bus: EventBus) -> None:
    log: list[str] = []

    bus.register(OrderCreated, lambda e: log.append("handler_1"))
    bus.register(OrderCreated, lambda e: log.append("handler_2"))

    bus.publish(OrderCreated())
    assert log == ["handler_1", "handler_2"]


def test_event_bus_handler_fallido_no_interrumpe_otros(bus: EventBus) -> None:
    log: list[str] = []

    bus.register(OrderCreated, lambda e: (_ for _ in ()).throw(Exception("fallo")))
    bus.register(OrderCreated, lambda e: log.append("handler_2_ok"))

    bus.publish(OrderCreated())
    assert "handler_2_ok" in log


def test_event_bus_sin_handlers_no_lanza_error(bus: EventBus) -> None:
    """Publicar un evento sin handlers no lanza excepción."""
    bus.publish(OrderCreated(order_id="ORD-999"))


def test_event_bus_publish_all(bus: EventBus) -> None:
    received: list[DomainEvent] = []
    bus.register(OrderCreated, received.append)
    bus.register(OrderStatusChanged, received.append)

    bus.publish_all(
        [
            OrderCreated(order_id="ORD-001"),
            OrderStatusChanged(order_id="ORD-001", old_status="pending", new_status="confirmed"),
        ]
    )
    assert len(received) == 2


# ---------------------------------------------------------------------------
# 4. PRUEBAS DE PRESENTERS
# ---------------------------------------------------------------------------


def test_json_presenter_devuelve_dict(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
    uow: InMemoryUnitOfWork,
    bus: EventBus,
) -> None:
    uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter())
    result = uc.execute(sample_command)

    assert isinstance(result, dict)
    assert result["order_id"] == "ORD-00001"
    assert result["customer_name"] == "Juan Pérez"
    assert result["status"] == "pending"
    assert result["total"] == pytest.approx(1399.97, rel=1e-2)
    assert len(result["items"]) == 2


def test_cli_presenter_devuelve_string(
    uow: InMemoryUnitOfWork, bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=CliPresenter())
    result = uc.execute(sample_command)

    assert isinstance(result, str)
    assert "ORD-00001" in result
    assert "Juan Pérez" in result
    assert "$1399.97" in result


def test_api_presenter_devuelve_order_out(
    uow: InMemoryUnitOfWork, bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    from order_management.schemas.schemas import OrderOut

    uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=ApiPresenter())
    result = uc.execute(sample_command)

    assert isinstance(result, OrderOut)
    assert result.order_id == "ORD-00001"
    assert result.status == "pending"


def test_audit_presenter_devuelve_payload_minimo(
    uow: InMemoryUnitOfWork, bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    uc = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=AuditPresenter())
    result = uc.execute(sample_command)

    assert isinstance(result, dict)
    assert result["event"] == "ORDER_CREATED"
    assert result["order_id"] == "ORD-00001"
    assert "total" in result


def test_presenters_cumplen_protocol() -> None:
    """Todos los presenters implementan OrderPresenterPort."""
    assert isinstance(JsonPresenter(), OrderPresenterPort)
    assert isinstance(CliPresenter(), OrderPresenterPort)
    assert isinstance(ApiPresenter(), OrderPresenterPort)
    assert isinstance(AuditPresenter(), OrderPresenterPort)


# ---------------------------------------------------------------------------
# 5. PRUEBAS DEL CASO DE USO v2 (UoW + eventos + presenter)
# ---------------------------------------------------------------------------


def test_create_order_v2_hace_commit(
    uow: InMemoryUnitOfWork, bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    CreateOrderUseCase(uow=uow, event_bus=bus).execute(sample_command)
    assert uow.was_committed is True


def test_create_order_v2_persiste_orden(
    uow: InMemoryUnitOfWork, bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    CreateOrderUseCase(uow=uow, event_bus=bus).execute(sample_command)
    orders = uow.orders.list_all()
    assert len(orders) == 1
    assert str(orders[0].order_id) == "ORD-00001"


def test_create_order_v2_publica_evento_order_created(
    bus: EventBus, sample_command: CreateOrderCommand
) -> None:
    received: list[OrderCreated] = []
    bus.register(OrderCreated, received.append)

    uow = InMemoryUnitOfWork()
    CreateOrderUseCase(uow=uow, event_bus=bus).execute(sample_command)

    assert len(received) == 1
    assert received[0].order_id == "ORD-00001"
    assert received[0].customer_email == "juan.perez@example.com"
    assert received[0].total == pytest.approx(Decimal("1399.97"), rel=Decimal("0.01"))


def test_create_order_v2_handler_notificacion_ejecutado(sample_command: CreateOrderCommand) -> None:
    """El handler de notificación se ejecuta automáticamente al publicar el evento."""
    notifications: list[dict[str, Any]] = []

    bus = EventBus()

    @bus.subscribe(OrderCreated)
    def notify(event: OrderCreated) -> None:
        notifications.append(
            {
                "order_id": event.order_id,
                "email": event.customer_email,
                "total": float(event.total),
            }
        )

    uow = InMemoryUnitOfWork()
    CreateOrderUseCase(uow=uow, event_bus=bus).execute(sample_command)

    assert len(notifications) == 1
    assert notifications[0]["order_id"] == "ORD-00001"
    assert notifications[0]["email"] == "juan.perez@example.com"


def test_create_order_v2_multiples_handlers_por_evento(sample_command: CreateOrderCommand) -> None:
    """Múltiples handlers (notificación + auditoría) se ejecutan para el mismo evento."""
    notify_log: list[str] = []
    audit_log: list[str] = []

    bus = EventBus()
    bus.register(OrderCreated, lambda e: notify_log.append(e.order_id))
    bus.register(OrderCreated, lambda e: audit_log.append(f"AUDIT:{e.order_id}"))

    uow = InMemoryUnitOfWork()
    CreateOrderUseCase(uow=uow, event_bus=bus).execute(sample_command)

    assert notify_log == ["ORD-00001"]
    assert audit_log == ["AUDIT:ORD-00001"]


def test_create_order_v2_separacion_capas() -> None:
    """
    Prueba de separación de capas:
    - El caso de uso NO importa nada de SQLAlchemy, httpx ni FastAPI
    - Funciona con cualquier UoW, EventBus y Presenter
    """
    # Verificar que create_order.py no importa infraestructura directamente
    import importlib
    import inspect

    module = importlib.import_module("order_management.application.use_cases.create_order")
    source = inspect.getsource(module)

    assert "sqlalchemy" not in source.lower()
    assert "fastapi" not in source.lower()
    assert "httpx" not in source.lower()
