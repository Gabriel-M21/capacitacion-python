"""
Pruebas de Arquitectura Hexagonal - Módulo 15
Cubre: dominio, contrato (LSP), caso de uso y adaptadores.
"""

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from order_management.application.dtos import CreateOrderCommand, OrderItemCommand
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
def use_case(
    memory_repo: InMemoryOrderRepository,
    memory_notifier: InMemoryNotificationAdapter,
) -> CreateOrderUseCase:
    return CreateOrderUseCase(
        repository=memory_repo,
        notifier=memory_notifier,
    )


# ---------------------------------------------------------------------------
# 1. PRUEBAS DE DOMINIO — sin infraestructura
# ---------------------------------------------------------------------------


def test_dominio_order_calcula_total_correctamente():
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


def test_dominio_order_status_transicion_valida():
    """pending → confirmed es una transición válida."""
    assert OrderStatus.PENDING.can_transition_to(OrderStatus.CONFIRMED)


def test_dominio_order_status_transicion_invalida():
    """pending → delivered NO es una transición válida."""
    assert not OrderStatus.PENDING.can_transition_to(OrderStatus.DELIVERED)


def test_dominio_money_no_acepta_negativo():
    with pytest.raises(ValueError):
        Money(Decimal("-1"), "USD")


def test_dominio_email_invalido_lanza_error():
    with pytest.raises(ValueError):
        Email("no-es-un-email")


def test_dominio_order_id_formato_correcto():
    oid = OrderId.generate(42)
    assert str(oid) == "ORD-00042"


def test_dominio_order_sin_items_lanza_error():
    customer = Customer(name="Test", email=Email("t@example.com"))
    with pytest.raises(ValueError, match="al menos un item"):
        Order(order_id=OrderId.generate(1), customer=customer, items=[])


# ---------------------------------------------------------------------------
# 2. PRUEBAS DE CONTRATO (LSP) — adaptadores intercambiables
# ---------------------------------------------------------------------------


def test_contrato_notification_port_cumplido_por_memory():
    """InMemoryNotificationAdapter cumple NotificationPort."""
    adapter = InMemoryNotificationAdapter()
    assert isinstance(adapter, NotificationPort)


def test_contrato_notification_port_cumplido_por_http():
    """HttpNotificationAdapter cumple NotificationPort."""
    adapter = HttpNotificationAdapter(base_url="http://localhost:8080")
    assert isinstance(adapter, NotificationPort)


def test_contrato_repository_port_cumplido_por_memory():
    """InMemoryOrderRepository cumple OrderRepositoryPort."""
    repo = InMemoryOrderRepository()
    assert isinstance(repo, OrderRepositoryPort)


def test_contrato_lsp_mismo_resultado_con_ambos_notificadores(
    memory_repo: InMemoryOrderRepository,
    sample_command: CreateOrderCommand,
) -> None:
    """
    LSP: CreateOrderUseCase produce el mismo resultado
    independientemente del notificador inyectado.
    """
    # Con InMemory
    notifier_mem = InMemoryNotificationAdapter()
    result_mem = CreateOrderUseCase(memory_repo, notifier_mem).execute(sample_command)

    # Con HTTP (mock para no necesitar red)
    memory_repo.clear()
    http_notifier = HttpNotificationAdapter(
        base_url="http://localhost:8080",
        raise_on_error=False,
    )
    with patch.object(http_notifier, "_post"):
        result_http = CreateOrderUseCase(memory_repo, http_notifier).execute(
            CreateOrderCommand(
                customer_name=sample_command.customer_name,
                customer_email=sample_command.customer_email,
                sequence_number=2,
                items=sample_command.items,
            )
        )

    # El resultado del caso de uso es idéntico con ambos notificadores
    assert result_mem.customer_name == result_http.customer_name
    assert result_mem.customer_email == result_http.customer_email
    assert result_mem.total == result_http.total
    assert result_mem.status == result_http.status
    assert result_mem.item_count == result_http.item_count


# ---------------------------------------------------------------------------
# 3. PRUEBAS DEL CASO DE USO CreateOrder
# ---------------------------------------------------------------------------


def test_create_order_retorna_resultado_correcto(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
) -> None:
    result = use_case.execute(sample_command)

    assert result.order_id == "ORD-00001"
    assert result.customer_name == "Juan Pérez"
    assert result.customer_email == "juan.perez@example.com"
    assert result.status == "pending"
    assert result.total == Decimal("1399.97")
    assert result.item_count == 2
    assert result.notes == "Entrega urgente"


def test_create_order_persiste_en_repositorio(
    use_case: CreateOrderUseCase,
    sample_command: CreateOrderCommand,
    memory_repo: InMemoryOrderRepository,
) -> None:
    use_case.execute(sample_command)
    orders = memory_repo.list_all()
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
    assert notif["event"] == "order_created"
    assert notif["customer_email"] == "juan.perez@example.com"
    assert notif["total"] == pytest.approx(1399.97, rel=1e-2)


def test_create_order_notificacion_fallida_no_rompe_flujo(
    memory_repo: InMemoryOrderRepository,
    sample_command: CreateOrderCommand,
) -> None:
    """
    Si el notificador falla, el caso de uso igual persiste la orden.
    La notificación es no crítica.
    """
    failing_notifier = MagicMock(spec=NotificationPort)
    failing_notifier.order_created.side_effect = Exception("Red caída")

    use_case = CreateOrderUseCase(
        repository=memory_repo,
        notifier=failing_notifier,
    )
    result = use_case.execute(sample_command)

    # La orden se creó aunque la notificación falló
    assert result.order_id == "ORD-00001"
    assert len(memory_repo.list_all()) == 1


def test_create_order_multiples_ordenes_secuenciales(
    memory_repo: InMemoryOrderRepository,
    memory_notifier: InMemoryNotificationAdapter,
) -> None:
    """Crear múltiples órdenes genera IDs únicos y notificaciones separadas."""
    for i in range(1, 4):
        cmd = CreateOrderCommand(
            customer_name="Cliente Test",
            customer_email="test@example.com",
            sequence_number=i,
            items=[OrderItemCommand("Producto", 1, Decimal("100.00"))],
        )
        CreateOrderUseCase(memory_repo, memory_notifier).execute(cmd)

    orders = memory_repo.list_all()
    assert len(orders) == 3

    ids = {str(o.order_id) for o in orders}
    assert ids == {"ORD-00001", "ORD-00002", "ORD-00003"}
    assert memory_notifier.notification_count == 3


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

    notifier = HttpNotificationAdapter(
        base_url="http://localhost:8080",
        raise_on_error=True,
    )
    use_case = CreateOrderUseCase(repository=memory_repo, notifier=notifier)
    result = use_case.execute(sample_command)

    assert result.order_id == "ORD-00001"
    assert result.customer_email == "juan.perez@example.com"
