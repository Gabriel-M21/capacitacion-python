"""
Demo del Módulo 16: Arquitectura Limpia
Demuestra:
  1. Eventos de dominio inmutables
  2. Unit of Work — atomicidad y rollback
  3. EventBus — múltiples handlers por evento
  4. Presenters — mismo caso de uso, 4 formatos de salida
  5. Flujo completo: comando → UoW → evento → handler → presenter
"""

from decimal import Decimal
from typing import Any

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
from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.events import OrderCreated, OrderStatusChanged
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_command(
    seq: int,
    name: str,
    email: str,
    items: list[tuple[str, int, float]],
    notes: str | None = None,
) -> CreateOrderCommand:
    return CreateOrderCommand(
        customer_name=name,
        customer_email=email,
        sequence_number=seq,
        notes=notes,
        items=[
            OrderItemCommand(product_name=p, quantity=q, unit_price=Decimal(str(pr)))
            for p, q, pr in items
        ],
    )


# ---------------------------------------------------------------------------
# DEMO 1 — Eventos de dominio inmutables
# ---------------------------------------------------------------------------


def demo_eventos() -> None:
    print("\n" + "=" * 65)
    print("1. EVENTOS DE DOMINIO — inmutables y con identidad propia")
    print("=" * 65)

    e1 = OrderCreated(
        order_id="ORD-00001",
        customer_email="juan.perez@example.com",
        customer_name="Juan Pérez",
        total=Decimal("1399.97"),
        item_count=2,
        status="pending",
    )
    e2 = OrderStatusChanged(
        order_id="ORD-00001",
        old_status="pending",
        new_status="confirmed",
    )

    print("\n  OrderCreated:")
    print(f"    event_id      : {e1.event_id}")
    print(f"    occurred_at   : {e1.occurred_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"    order_id      : {e1.order_id}")
    print(f"    customer      : {e1.customer_name} <{e1.customer_email}>")
    print(f"    total         : ${e1.total:.2f}")

    print("\n  OrderStatusChanged:")
    print(f"    event_id      : {e2.event_id}")
    print(f"    order_id      : {e2.order_id}")
    print(f"    transición    : {e2.old_status} → {e2.new_status}")

    print(f"\n  IDs únicos por evento: {e1.event_id != e2.event_id}")

    # Verificar inmutabilidad
    try:
        e1.order_id = "OTRO"  # type: ignore[misc]
    except (AttributeError, TypeError):
        print("  ✓ Inmutabilidad verificada — no se puede modificar el evento")


# ---------------------------------------------------------------------------
# DEMO 2 — Unit of Work — atomicidad
# ---------------------------------------------------------------------------


def demo_uow() -> None:
    print("\n" + "=" * 65)
    print("2. UNIT OF WORK — atomicidad y rollback automático")
    print("=" * 65)

    # 2A — Flujo exitoso
    print("\n  2A. Flujo exitoso (commit):")
    uow = InMemoryUnitOfWork()

    order = Order(
        order_id=OrderId.generate(1),
        customer=Customer("Juan Pérez", Email("juan.perez@example.com")),
        items=[OrderItem("Laptop", 1, Money(Decimal("1299.99"), "USD"))],
    )

    with uow:
        uow.orders.save(order)
        uow.add_event(OrderCreated(order_id=str(order.order_id)))
        uow.commit()

    print(f"    Órdenes en repo   : {len(uow.orders.list_all())}")
    print(f"    commit() llamado  : {uow.was_committed}")
    events = uow.collect_events()
    print(f"    Eventos pendientes: {len(events)}")

    # 2B — Rollback por excepción
    print("\n  2B. Rollback automático por excepción:")
    uow2 = InMemoryUnitOfWork()

    try:
        with uow2:
            uow2.orders.save(order)
            raise RuntimeError("Error simulado en medio de la transacción")
    except RuntimeError:
        pass

    print(f"    Órdenes en repo   : {len(uow2.orders.list_all())}  ← rollback aplicado")
    print(f"    commit() llamado  : {uow2.was_committed}")


# ---------------------------------------------------------------------------
# DEMO 3 — EventBus — múltiples handlers
# ---------------------------------------------------------------------------


def demo_event_bus() -> None:
    print("\n" + "=" * 65)
    print("3. EVENT BUS — múltiples handlers desacoplados")
    print("=" * 65)

    bus = EventBus()
    log: list[str] = []

    # Handler 1: notificación al cliente
    @bus.subscribe(OrderCreated)
    def notify_customer(event: OrderCreated) -> None:
        log.append(f"Email enviado a {event.customer_email} — total ${event.total:.2f}")

    # Handler 2: actualizar métricas
    @bus.subscribe(OrderCreated)
    def update_metrics(event: OrderCreated) -> None:
        log.append(f"Métricas actualizadas — orden {event.order_id}")

    # Handler 3: auditoría
    @bus.subscribe(OrderCreated)
    def audit_log(event: OrderCreated) -> None:
        log.append(
            f"Auditoría: ORDER_CREATED {event.order_id} a las {event.occurred_at.strftime('%H:%M:%S')}"
        )

    # Handler para cambio de estado
    @bus.subscribe(OrderStatusChanged)
    def on_status_change(event: OrderStatusChanged) -> None:
        log.append(f"Estado cambiado: {event.order_id} {event.old_status} → {event.new_status}")

    # Publicar eventos
    print(f"\n  Handlers registrados para OrderCreated    : {bus.handler_count(OrderCreated)}")
    print(
        f"  Handlers registrados para OrderStatusChanged: {bus.handler_count(OrderStatusChanged)}"
    )

    bus.publish(
        OrderCreated(
            order_id="ORD-00042",
            customer_email="ana.martinez@example.com",
            total=Decimal("857.00"),
        )
    )
    bus.publish(
        OrderStatusChanged(
            order_id="ORD-00042",
            old_status="pending",
            new_status="confirmed",
        )
    )

    print(f"\n  Resultado de publicar 2 eventos ({len(log)} acciones ejecutadas):")
    for entry in log:
        print(f"    {entry}")


# ---------------------------------------------------------------------------
# DEMO 4 — Presenters — mismo caso de uso, 4 formatos
# ---------------------------------------------------------------------------


def demo_presenters() -> None:
    print("\n" + "=" * 65)
    print("4. PRESENTERS — mismo caso de uso, 4 formatos de salida")
    print("=" * 65)

    command = _make_command(
        seq=99,
        name="Laura Gómez",
        email="laura.gomez@example.com",
        items=[
            ("MacBook Air M3", 1, 1299.99),
            ("Magic Mouse", 1, 79.00),
            ("Cable USB-C 2m", 2, 24.99),
        ],
        notes="Cliente VIP",
    )

    presenters: dict[str, OrderPresenterPort] = {
        "JsonPresenter  (API/webhook)": JsonPresenter(),
        "CliPresenter   (terminal)": CliPresenter(),
        "ApiPresenter   (FastAPI)": ApiPresenter(),
        "AuditPresenter (auditoría)": AuditPresenter(),
    }

    for label, presenter in presenters.items():
        uow = InMemoryUnitOfWork()
        bus = EventBus()
        result = CreateOrderUseCase(uow=uow, event_bus=bus, presenter=presenter).execute(command)

        print(f"\n  ── {label} ──")
        if isinstance(result, dict):
            import json

            preview = json.dumps(result, indent=4, default=str)
            lines = preview.split("\n")
            for line in lines[:8]:
                print(f"    {line}")
            if len(lines) > 8:
                print(f"    ... ({len(lines) - 8} líneas más)")
        elif isinstance(result, str):
            for line in result.split("\n"):
                print(f"    {line}")
        else:
            # OrderOut (Pydantic)
            print(f"    type      : {type(result).__name__}")
            print(f"    order_id  : {result.order_id}")
            print(f"    total     : {result.total}")
            print(f"    status    : {result.status}")


# ---------------------------------------------------------------------------
# DEMO 5 — Flujo completo integrado
# ---------------------------------------------------------------------------


def demo_flujo_completo() -> None:
    print("\n" + "=" * 65)
    print("5. FLUJO COMPLETO — Comando → UoW → Evento → Handler → Presenter")
    print("=" * 65)

    # Setup del bus con handlers reales
    bus = EventBus()
    notifications: list[dict[str, Any]] = []
    audit_trail: list[str] = []

    @bus.subscribe(OrderCreated)
    def send_notification(event: OrderCreated) -> None:
        notifications.append(
            {
                "to": event.customer_email,
                "total": float(event.total),
            }
        )

    @bus.subscribe(OrderCreated)
    def record_audit(event: OrderCreated) -> None:
        audit_trail.append(
            f"[{event.occurred_at.strftime('%H:%M:%S')}] "
            f"ORDER_CREATED {event.order_id} — {event.customer_name}"
        )

    @bus.subscribe(OrderStatusChanged)
    def record_status_audit(event: OrderStatusChanged) -> None:
        audit_trail.append(
            f"[{event.occurred_at.strftime('%H:%M:%S')}] "
            f"STATUS_CHANGE {event.order_id}: {event.old_status}→{event.new_status}"
        )

    # Ejecutar caso de uso
    uow = InMemoryUnitOfWork()
    command = _make_command(
        seq=1,
        name="Pedro Ramírez",
        email="pedro.ramirez@example.com",
        items=[
            ("Samsung Galaxy S24", 1, 999.99),
            ("Cargador inalámbrico", 1, 39.99),
            ("Funda premium", 1, 29.99),
        ],
        notes="Envío express",
    )

    result = CreateOrderUseCase(
        uow=uow,
        event_bus=bus,
        presenter=CliPresenter(),
    ).execute(command)

    # Simular cambio de estado y publicarlo manualmente
    orders = uow.orders.list_all()
    if orders:
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

    # Mostrar resultado
    print("\n  Resultado del caso de uso (CliPresenter):")
    for line in result.split("\n"):
        print(f"    {line}")

    print("\n  UoW:")
    print(f"    commit() ejecutado : {uow.was_committed}")
    print(f"    Órdenes en repo    : {len(uow.orders.list_all())}")

    print(f"\n  Notificaciones enviadas ({len(notifications)}):")
    for n in notifications:
        print(f"    → {n['to']}  total: ${n['total']:.2f}")

    print(f"\n  Trail de auditoría ({len(audit_trail)} entradas):")
    for entry in audit_trail:
        print(f"    {entry}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 65)
    print("MÓDULO 16: ARQUITECTURA LIMPIA")
    print("Eventos · UoW · EventBus · Presenters · Capas")
    print("=" * 65)

    demo_eventos()
    demo_uow()
    demo_event_bus()

    demo_presenters()
    demo_flujo_completo()

    print("\n" + "=" * 65)
    print("✓ DEMO MÓDULO 16 COMPLETADO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
