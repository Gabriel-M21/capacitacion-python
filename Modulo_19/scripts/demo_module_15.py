"""
Demo del Módulo 15: Arquitectura Hexagonal (Puertos y Adaptadores)
Demuestra:
  1. Caso de uso CreateOrder con adaptador en memoria
  2. Caso de uso CreateOrder con adaptador HTTP (Smocker)
  3. Resiliencia: notificación fallida no rompe el flujo
  4. LSP: mismo resultado con distintos adaptadores
  5. Wiring completo: DTOs → caso de uso → dominio → persistencia → notificación
"""

from decimal import Decimal

import httpx

from order_management.application.dtos import (
    CreateOrderCommand,
    OrderCreatedResult,
    OrderItemCommand,
)
from order_management.application.use_cases.create_order import CreateOrderUseCase
from order_management.domain.value_objects import OrderStatus
from order_management.infrastructure.adapters.http_notification import HttpNotificationAdapter
from order_management.infrastructure.adapters.memory_notification import InMemoryNotificationAdapter
from order_management.infrastructure.db.repositories.in_memory_order_repo import (
    InMemoryOrderRepository,
)

SMOCKER_URL = "http://localhost:8080"
SMOCKER_ADMIN = "http://localhost:8081"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_notification_mock() -> bool:
    """Registra el mock de notificaciones en Smocker. Retorna True si lo logra."""
    mock_yaml = """
- request:
    method: POST
    path: /notifications/orders
  response:
    status: 200
    headers:
      Content-Type: application/json
    body: '{"status": "notification_received"}'
"""
    try:
        resp = httpx.post(
            f"{SMOCKER_ADMIN}/mocks",
            content=mock_yaml,
            headers={"Content-Type": "application/x-yaml"},
            timeout=2.0,
        )
        return resp.is_success
    except httpx.RequestError:
        return False


def _smocker_available() -> bool:
    """Verifica si Smocker está activo."""
    try:
        httpx.get(f"{SMOCKER_ADMIN}/version", timeout=1.0)
        return True
    except httpx.RequestError:
        return False


def _print_result(result: "OrderCreatedResult", label: str = "") -> None:
    """Imprime un OrderCreatedResult de forma legible."""
    if label:
        print(f"\n  [{label}]")
    print(f"  order_id      : {result.order_id}")
    print(f"  cliente       : {result.customer_name} <{result.customer_email}>")
    print(f"  estado        : {result.status}")
    print(f"  total         : ${result.total:.2f}")
    print(f"  items         : {result.item_count}")
    for item in result.items:
        print(f"    • {item.product_name:<35} x{item.quantity}  ${item.subtotal:.2f}")
    if result.notes:
        print(f"  notas         : {result.notes}")


# ---------------------------------------------------------------------------
# DEMO 1 — CreateOrder con adaptador en memoria
# ---------------------------------------------------------------------------


def demo_memoria() -> None:
    print("\n" + "=" * 65)
    print("1. CreateOrder — Adaptador EN MEMORIA")
    print("   (sin base de datos ni red)")
    print("=" * 65)

    repo = InMemoryOrderRepository()
    notifier = InMemoryNotificationAdapter()
    use_case = CreateOrderUseCase(repository=repo, notifier=notifier)

    command = CreateOrderCommand(
        customer_name="Juan Pérez",
        customer_email="juan.perez@example.com",
        customer_phone="+52 55 1234 5678",
        sequence_number=1,
        notes="Entrega urgente",
        items=[
            OrderItemCommand("Laptop Dell XPS 15", 1, Decimal("1299.99")),
            OrderItemCommand("Mouse Logitech MX Master", 2, Decimal("49.99")),
            OrderItemCommand("Teclado mecánico", 1, Decimal("129.50")),
        ],
    )

    result = use_case.execute(command)
    _print_result(result, "Resultado")

    print("\n  Repositorio en memoria:")
    orders = repo.list_all()
    print(f"    Órdenes guardadas : {len(orders)}")
    print(f"    Estado en dominio : {orders[0].status.value}")

    print("\n  Notificaciones enviadas:")
    print(f"    Total             : {notifier.notification_count}")
    notif = notifier.last_notification
    if notif:
        print(f"    Evento            : {notif['event']}")
        print(f"    order_id          : {notif['order_id']}")
        print(f"    customer_email    : {notif['customer_email']}")
        print(f"    total             : ${notif['total']:.2f}")


# ---------------------------------------------------------------------------
# DEMO 2 — CreateOrder con adaptador HTTP (Smocker)
# ---------------------------------------------------------------------------


def demo_smocker() -> None:
    print("\n" + "=" * 65)
    print("2. CreateOrder — Adaptador HTTP (Smocker)")
    print("=" * 65)

    if not _smocker_available():
        print("\n  ⚠ Smocker no está disponible — omitiendo esta sección.")
        print("  Levántalo con: docker start smocker")
        return

    if not _register_notification_mock():
        print("\n  ⚠ No se pudo registrar el mock en Smocker.")
        return

    print("\n  ✓ Smocker activo y mock registrado en /notifications/orders")

    repo = InMemoryOrderRepository()
    notifier = HttpNotificationAdapter(
        base_url=SMOCKER_URL,
        timeout=3.0,
        raise_on_error=False,
    )
    use_case = CreateOrderUseCase(repository=repo, notifier=notifier)

    command = CreateOrderCommand(
        customer_name="Laura Gómez",
        customer_email="laura.gomez@example.com",
        sequence_number=10,
        notes="Cliente VIP — máxima prioridad",
        items=[
            OrderItemCommand("MacBook Air M3", 1, Decimal("1299.99")),
            OrderItemCommand("Magic Mouse", 1, Decimal("79.00")),
            OrderItemCommand("Cable USB-C 2m", 2, Decimal("24.99")),
        ],
    )

    result = use_case.execute(command)
    _print_result(result, "Resultado")
    print("\n  ✓ Notificación HTTP enviada a Smocker (POST /notifications/orders)")


# ---------------------------------------------------------------------------
# DEMO 3 — Resiliencia: notificación fallida no rompe el flujo
# ---------------------------------------------------------------------------


def demo_resiliencia() -> None:
    print("\n" + "=" * 65)
    print("3. RESILIENCIA — Notificación fallida no rompe el flujo")
    print("=" * 65)

    repo = InMemoryOrderRepository()

    # Notificador que apunta a un host inexistente
    notifier = HttpNotificationAdapter(
        base_url="http://host-inexistente-12345.example",
        timeout=0.5,
        raise_on_error=False,  # ← clave: no propaga el error
    )
    use_case = CreateOrderUseCase(repository=repo, notifier=notifier)

    command = CreateOrderCommand(
        customer_name="Carlos López",
        customer_email="carlos.lopez@example.com",
        sequence_number=20,
        items=[
            OrderItemCommand("SSD 1TB", 1, Decimal("89.99")),
        ],
    )

    print("\n  Ejecutando caso de uso con notificador caído...")
    result = use_case.execute(command)

    print("\n  ✓ Orden creada exitosamente a pesar del fallo de red:")
    print(f"    order_id : {result.order_id}")
    print(f"    total    : ${result.total:.2f}")
    print(f"    estado   : {result.status}")
    print("\n  ✓ Dominio íntegro — la orden está en el repositorio:")
    print(f"    Órdenes en repo : {len(repo.list_all())}")


# ---------------------------------------------------------------------------
# DEMO 4 — LSP: mismo resultado con distintos adaptadores
# ---------------------------------------------------------------------------


def demo_lsp() -> None:
    print("\n" + "=" * 65)
    print("4. LSP — Mismo resultado con distintos adaptadores")
    print("=" * 65)

    # Con InMemory
    repo_mem = InMemoryOrderRepository()
    notif_mem = InMemoryNotificationAdapter()
    result_mem = CreateOrderUseCase(repo_mem, notif_mem).execute(
        CreateOrderCommand(
            customer_name="Ana Martínez",
            customer_email="ana.martinez@example.com",
            sequence_number=30,
            items=[
                OrderItemCommand("Tablet iPad Air", 1, Decimal("649.00")),
                OrderItemCommand("Apple Pencil", 1, Decimal("129.00")),
            ],
        )
    )

    # Con HTTP (Smocker o fallback silencioso)
    repo_http = InMemoryOrderRepository()
    notif_http = HttpNotificationAdapter(
        base_url=SMOCKER_URL if _smocker_available() else "http://localhost:9999",
        raise_on_error=False,
    )
    result_http = CreateOrderUseCase(repo_http, notif_http).execute(
        CreateOrderCommand(
            customer_name="Ana Martínez",
            customer_email="ana.martinez@example.com",
            sequence_number=30,
            items=[
                OrderItemCommand("Tablet iPad Air", 1, Decimal("649.00")),
                OrderItemCommand("Apple Pencil", 1, Decimal("129.00")),
            ],
        )
    )

    print(f"\n  {'Campo':<20} {'InMemory':>15}  {'HTTP':>15}  {'Igual?':>8}")
    print("  " + "-" * 65)

    checks = [
        ("order_id", result_mem.order_id, result_http.order_id),
        ("customer_name", result_mem.customer_name, result_http.customer_name),
        ("status", result_mem.status, result_http.status),
        ("total", f"${result_mem.total:.2f}", f"${result_http.total:.2f}"),
        ("item_count", str(result_mem.item_count), str(result_http.item_count)),
    ]

    all_equal = True
    for field, val_mem, val_http in checks:
        equal = "✓" if val_mem == val_http else "✗"
        all_equal = all_equal and (val_mem == val_http)
        print(f"  {field:<20} {str(val_mem):>15}  {str(val_http):>15}  {equal:>8}")

    print(
        f"\n  {'✓ LSP verificado' if all_equal else '✗ LSP fallido'}: "
        f"ambos adaptadores producen el mismo resultado"
    )


# ---------------------------------------------------------------------------
# DEMO 5 — Cambio de estado y ciclo de vida de la orden
# ---------------------------------------------------------------------------


def demo_ciclo_vida() -> None:
    print("\n" + "=" * 65)
    print("5. CICLO DE VIDA — Transiciones de estado en dominio")
    print("=" * 65)

    repo = InMemoryOrderRepository()
    notifier = InMemoryNotificationAdapter()
    use_case = CreateOrderUseCase(repository=repo, notifier=notifier)

    result = use_case.execute(
        CreateOrderCommand(
            customer_name="Pedro Ramírez",
            customer_email="pedro.ramirez@example.com",
            sequence_number=40,
            items=[
                OrderItemCommand("Samsung Galaxy S24", 1, Decimal("999.99")),
                OrderItemCommand("Cargador inalámbrico", 1, Decimal("39.99")),
            ],
        )
    )

    order = repo.get_by_order_id(result.order_id)
    if order is None:
        print("  Error: orden no encontrada")
        return

    transitions = [
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ]

    print(f"\n  Orden: {order.order_id}  Total: {order.total}")
    print(f"\n  {'Paso':<5} {'Desde':<12} {'Hacia':<12} {'Resultado':<12}")
    print("  " + "-" * 45)
    print(f"  {'0':<5} {'-':<12} {'pending':<12} ✓ creada")

    for step, new_status in enumerate(transitions, 1):
        old = order.status.value
        try:
            order.change_status(new_status)
            notifier.order_status_changed(
                order_id=str(order.order_id),
                old_status=old,
                new_status=order.status.value,
            )
            print(f"  {step:<5} {old:<12} {order.status.value:<12} ✓")
        except ValueError as e:
            print(f"  {step:<5} {old:<12} {new_status.value:<12} ✗ {e}")

    print(f"\n  Notificaciones totales enviadas : {notifier.notification_count}")
    print(f"  (1 order_created + {len(transitions)} order_status_changed)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 65)
    print("MÓDULO 15: ARQUITECTURA HEXAGONAL")
    print("Puertos · Adaptadores · Casos de Uso · DTOs · LSP")
    print("=" * 65)

    demo_memoria()
    demo_smocker()
    demo_resiliencia()
    demo_lsp()
    demo_ciclo_vida()

    print("\n" + "=" * 65)
    print("✓ DEMO MÓDULO 15 COMPLETADO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
