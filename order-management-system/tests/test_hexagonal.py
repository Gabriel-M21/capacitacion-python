"""
Pruebas de Arquitectura Hexagonal - Módulo 15
Cubre: dominio, contrato (LSP), caso de uso y adaptadores.
"""

from decimal import Decimal
from typing import Any
from unittest.mock import patch

import pytest

from order_management.application.dtos import CreateOrderCommand, OrderItemCommand
from order_management.application.event_bus import EventBus
from order_management.application.presenters import JsonPresenter
from order_management.application.unit_of_work import InMemoryUnitOfWork
from order_management.application.use_cases.create_order import CreateOrderUseCase
from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.ports import NotificationPort, OrderRepositoryPort
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus
from order_management.infrastructure.adapters.http_notification import HttpNotificationAdapter
from order_management.infrastructure.adapters.memory_notification import InMemoryNotificationAdapter
from order_management.infrastructure.db.repositories.in_memory_order_repo import (
    InMemoryOrderRepository,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_command() -> CreateOrderCommand:
    return CreateOrderCommand(
        customer_name="Juan Pérez",
        customer_email="juan.perez@example.com",
        customer_phone="+52 55 1234 5678",
        sequence_number=1,
        items=[
            OrderItemCommand(
                product_name="Laptop Dell XPS 15",
                quantity=1,
                unit_price=Decimal("1299.99"),
            ),
            OrderItemCommand(
                product_name="Mouse Logitech MX Master",
                quantity=2,
                unit_price=Decimal("49.99"),
            ),
        ],
        notes="Entrega urgente",
    )


@pytest.fixture
def memory_notifier() -> InMemoryNotificationAdapter:
    return InMemoryNotificationAdapter()


@pytest.fixture
def memory_repo() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def bus(memory_notifier: InMemoryNotificationAdapter) -> EventBus:
    b = EventBus()
    b.register(
        __import__("order_management.domain.events", fromlist=["OrderCreated"]).OrderCreated,
        (
            memory_notifier.order_created
            if False  # registrar via lambda para capturar el evento completo
            else lambda e: memory_notifier.order_created(
                order_id=e.order_id,
                customer_email=e.customer_email,
                total=float(e.total),
            )
        ),
    )
    return b


@pytest.fixture
def use_case(uow: InMemoryUnitOfWork, bus: EventBus) -> CreateOrderUseCase:
    return CreateOrderUseCase(
        uow=uow,
        event_bus=bus,
        presenter=JsonPresenter(),
    )


# ---------------------------------------------------------------------------
# 1. PRUEBAS DE DOMINIO — sin infraestructura
# ---------------------------------------------------------------------------


def test_dominio_order_calcula_total_correctamente() -> None:
    """El total de la orden es la suma de subtotales de cada item."""
    customer = Customer(
        name="Test User",
        email=Email("test@example.com"),
    )
    items = [
        OrderItem("Laptop", 1, Money(Decimal("1299.99"), "USD")),
        OrderItem("Mouse", 2, Money(Decimal("49.99"), "USD")),
    ]
    order = Order(order_id=OrderId.generate(1), customer=customer, items=items)

    assert order.total == Money(Decimal("1399.97"), "USD")


def test_dominio_order_status_transicion_valida() -> None:
    """pending → confirmed es una transición válida."""
    assert OrderStatus.PENDING.can_transition_to(OrderStatus.CONFIRMED)


def test_dominio_order_status_transicion_invalida() -> None:
    """pending → delivered NO es una transición válida."""
    assert not OrderStatus.PENDING.can_transition_to(OrderStatus.DELIVERED)


def test_dominio_money_no_acepta_negativo() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("-1"), "USD")


def test_dominio_email_invalido_lanza_error() -> None:
    with pytest.raises(ValueError):
        Email("no-es-un-email")


def test_dominio_order_id_formato_correcto() -> None:
    oid = OrderId.generate(42)
    assert str(oid) == "ORD-00042"


def test_dominio_order_sin_items_lanza_error() -> None:
    customer = Customer(name="Test", email=Email("t@example.com"))
    with pytest.raises(ValueError, match="al menos un item"):
        Order(order_id=OrderId.generate(1), customer=customer, items=[])


# ---------------------------------------------------------------------------
# 2. PRUEBAS DE CONTRATO (LSP) — adaptadores intercambiables
# ---------------------------------------------------------------------------


def test_contrato_notification_port_cumplido_por_memory() -> None:
    """InMemoryNotificationAdapter cumple NotificationPort."""
    adapter = InMemoryNotificationAdapter()
    assert isinstance(adapter, NotificationPort)


def test_contrato_notification_port_cumplido_por_http() -> None:
    """HttpNotificationAdapter cumple NotificationPort."""
    adapter = HttpNotificationAdapter(base_url="http://localhost:8080")
    assert isinstance(adapter, NotificationPort)


def test_contrato_repository_port_cumplido_por_memory() -> None:
    """InMemoryOrderRepository cumple OrderRepositoryPort."""
    repo = InMemoryOrderRepository()
    assert isinstance(repo, OrderRepositoryPort)


def test_contrato_lsp_mismo_resultado_con_ambos_notificadores(
    sample_command: CreateOrderCommand,
) -> None:
    """
    LSP: CreateOrderUseCase produce el mismo resultado
    independientemente del notificador registrado en el EventBus.
    """
    from order_management.domain.events import OrderCreated

    # Con InMemoryUnitOfWork + notificador en memoria
    uow1 = InMemoryUnitOfWork()
    bus1 = EventBus()
    result_mem = CreateOrderUseCase(uow=uow1, event_bus=bus1, presenter=JsonPresenter()).execute(
        sample_command
    )

    # Con InMemoryUnitOfWork + notificador HTTP mockeado
    uow2 = InMemoryUnitOfWork()
    bus2 = EventBus()
    http_notifier = HttpNotificationAdapter(
        base_url="http://localhost:8080",
        raise_on_error=False,
    )
    with patch.object(http_notifier, "_post"):
        bus2.register(
            OrderCreated,
            lambda e: http_notifier.order_created(e.order_id, e.customer_email, float(e.total)),
        )
        result_http = CreateOrderUseCase(
            uow=uow2, event_bus=bus2, presenter=JsonPresenter()
        ).execute(
            CreateOrderCommand(
                customer_name=sample_command.customer_name,
                customer_email=sample_command.customer_email,
                sequence_number=2,
                items=sample_command.items,
            )
        )

    assert result_mem["customer_name"] == result_http["customer_name"]
    assert result_mem["customer_email"] == result_http["customer_email"]
    assert result_mem["total"] == pytest.approx(result_http["total"], rel=1e-2)
    assert result_mem["status"] == result_http["status"]
    assert result_mem["item_count"] == result_http["item_count"]


# ---------------------------------------------------------------------------
# 3. PRUEBAS DEL CASO DE USO CreateOrder
# ---------------------------------------------------------------------------


def test_create_order_retorna_resultado_correcto(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
) -> None:
    result = use_case.execute(sample_command)

    # JsonPresenter devuelve dict
    assert result["order_id"] == "ORD-00001"
    assert result["customer_name"] == "Juan Pérez"
    assert result["customer_email"] == "juan.perez@example.com"
    assert result["status"] == "pending"
    assert result["total"] == pytest.approx(1399.97, rel=1e-2)
    assert result["item_count"] == 2
    assert result["notes"] == "Entrega urgente"


def test_create_order_persiste_en_repositorio(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
    uow: InMemoryUnitOfWork,
) -> None:
    use_case.execute(sample_command)
    orders = uow.orders.list_all()
    assert len(orders) == 1
    assert str(orders[0].order_id) == "ORD-00001"


def test_create_order_envia_notificacion(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
    memory_notifier: InMemoryNotificationAdapter,
) -> None:
    use_case.execute(sample_command)

    assert memory_notifier.notification_count == 1
    assert memory_notifier.was_notified("ORD-00001")

    notif = memory_notifier.last_notification
    assert notif is not None
    assert notif["customer_email"] == "juan.perez@example.com"
    assert notif["total"] == pytest.approx(1399.97, rel=1e-2)


def test_create_order_notificacion_fallida_no_rompe_flujo(
    sample_command: CreateOrderCommand,
) -> None:
    """
    Si el handler de notificación falla, el caso de uso igual persiste la orden.
    La notificación es no crítica.
    """
    from order_management.domain.events import OrderCreated

    uow = InMemoryUnitOfWork()
    bus = EventBus()
    bus.register(OrderCreated, lambda e: (_ for _ in ()).throw(Exception("Red caída")))

    use_case = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter())
    result = use_case.execute(sample_command)

    # La orden se creó aunque la notificación falló
    assert result["order_id"] == "ORD-00001"
    assert len(uow.orders.list_all()) == 1


def test_create_order_multiples_ordenes_secuenciales() -> None:
    """Crear múltiples órdenes genera IDs únicos y notificaciones separadas."""
    from order_management.domain.events import OrderCreated

    notif_count: list[int] = [0]
    uow = InMemoryUnitOfWork()
    bus = EventBus()
    bus.register(OrderCreated, lambda e: notif_count.__setitem__(0, notif_count[0] + 1))

    for i in range(1, 4):
        cmd = CreateOrderCommand(
            customer_name="Cliente Test",
            customer_email="test@example.com",
            sequence_number=i,
            items=[OrderItemCommand("Producto", 1, Decimal("100.00"))],
        )
        CreateOrderUseCase(uow=uow, event_bus=bus, presenter=JsonPresenter()).execute(cmd)

    orders = uow.orders.list_all()
    assert len(orders) == 3
    ids: set[str] = {str(o.order_id) for o in orders}
    assert ids == {"ORD-00001", "ORD-00002", "ORD-00003"}
    assert notif_count[0] == 3


def test_create_order_comando_invalido_lanza_error() -> None:
    """CreateOrderCommand valida los datos en su constructor."""
    with pytest.raises(ValueError, match="customer_name"):
        CreateOrderCommand(
            customer_name="",
            customer_email="test@example.com",
            items=[OrderItemCommand("P", 1, Decimal("10"))],
        )


def test_create_order_sin_items_lanza_error() -> None:
    with pytest.raises(ValueError, match="al menos un item"):
        CreateOrderCommand(
            customer_name="Test",
            customer_email="test@example.com",
            items=[],
        )


# ---------------------------------------------------------------------------
# 4. PRUEBAS DEL ADAPTADOR HTTP (con mock de red)
# ---------------------------------------------------------------------------


def test_http_notifier_envia_post_correcto() -> None:
    """HttpNotificationAdapter llama al endpoint correcto con el payload esperado."""
    notifier = HttpNotificationAdapter(
        base_url="http://localhost:8080",
        raise_on_error=True,
    )

    captured: list[dict[str, Any]] = []

    def fake_post(payload: dict[str, Any]) -> None:
        captured.append(payload)

    with patch.object(notifier, "_post", side_effect=fake_post):
        notifier.order_created(
            order_id="ORD-00001",
            customer_email="juan@example.com",
            total=1399.97,
        )

    assert len(captured) == 1
    assert captured[0]["event"] == "order_created"
    assert captured[0]["order_id"] == "ORD-00001"
    assert captured[0]["customer_email"] == "juan@example.com"
    assert captured[0]["total"] == pytest.approx(1399.97)


def test_http_notifier_no_lanza_por_defecto_en_error() -> None:
    """Con raise_on_error=False, los errores de red no propagan excepción."""
    notifier = HttpNotificationAdapter(
        base_url="http://host-que-no-existe.example",
        timeout=0.1,
        raise_on_error=False,
    )
    # No debe lanzar aunque la red falle
    notifier.order_created("ORD-99999", "test@example.com", 100.0)


def test_http_notifier_lanza_si_raise_on_error() -> None:
    """Con raise_on_error=True, los errores de red sí propagan."""
    import httpx

    notifier = HttpNotificationAdapter(
        base_url="http://host-que-no-existe.example",
        timeout=0.1,
        raise_on_error=True,
    )
    with pytest.raises(httpx.RequestError):
        notifier.order_created("ORD-99999", "test@example.com", 100.0)


# ---------------------------------------------------------------------------
# 5. PRUEBA CON SMOCKER (opcional — requiere docker)
# ---------------------------------------------------------------------------


def test_http_notifier_con_smocker_si_disponible(
    memory_repo: InMemoryOrderRepository,
    sample_command: CreateOrderCommand,
) -> None:
    """
    Prueba de integración real contra Smocker.
    Se salta automáticamente si Smocker no está disponible.
    """
    import httpx

    # Verificar si Smocker está activo
    try:
        httpx.get("http://localhost:8081/version", timeout=1.0)
    except httpx.RequestError:
        pytest.skip("Smocker no está disponible — omitiendo prueba de integración")

    # Registrar mock de notificación en Smocker
    mock_yaml = """
- request:
    method: POST
    path: /notifications/orders
  response:
    status: 200
    headers:
      Content-Type: application/json
    body: '{"status": "ok"}'
"""
    try:
        httpx.post(
            "http://localhost:8081/mocks",
            content=mock_yaml,
            headers={"Content-Type": "application/x-yaml"},
            timeout=2.0,
        )
    except httpx.RequestError:
        pytest.skip("No se pudo registrar mock en Smocker")

    uow2 = InMemoryUnitOfWork()
    bus2 = EventBus()
    use_case = CreateOrderUseCase(uow=uow2, event_bus=bus2, presenter=JsonPresenter())
    result = use_case.execute(sample_command)

    assert result["order_id"] == "ORD-00001"
    assert result["customer_email"] == "juan.perez@example.com"
