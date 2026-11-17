"""
Demo del Módulo 12: SOLID en acción
Muestra cómo OrderService trabaja con distintas implementaciones
sin cambiar una sola línea del servicio.
"""
from pathlib import Path
from typing import Any

from order_management.infrastructure.db.repositories.in_memory_order_repo import (
    InMemoryOrderRepository,
)
from order_management.infrastructure.db.repositories.json_order_repo import JsonFileOrderRepository
from order_management.services.order_service import OrderService


def demo_con_memoria() -> None:
    """DIP + LSP: OrderService con repositorio en memoria."""
    print("\n" + "=" * 60)
    print("1. CON InMemoryOrderRepository")
    print("=" * 60)

    repo = InMemoryOrderRepository(
        orders=[
            {
                "order_id": "ORD-001",
                "customer_name": "Juan Pérez",
                "email": "juan.perez@example.com",
                "status": "confirmed",
                "items": [
                    {
                        "product_name": "Laptop Dell XPS 15",
                        "quantity": 1,
                        "price": 1299.99,
                    },
                    {"product_name": "Mouse Logitech", "quantity": 2, "price": 29.99},
                ],
            },
            {
                "order_id": "ORD-002",
                "customer_name": "María García",
                "email": "maria.garcia@example.com",
                "status": "pending",
                "items": [
                    {
                        "product_name": "Teclado mecánico",
                        "quantity": 2,
                        "price": 129.50,
                    },
                ],
            },
            {
                # Orden inválida — sin email
                "order_id": "ORD-INV",
                "customer_name": "Sin Email",
                "status": "pending",
                "items": [{"product_name": "Producto X", "quantity": 1, "price": 10.0}],
            },
        ]
    )

    service = OrderService(repository=repo)
    result = service.process_orders(skip_invalid=True)

    print(f"\n  Válidas      : {result['valid_orders']}")
    print(f"  Inválidas    : {result['invalid_orders']}")
    print(f"  Revenue      : ${result['total_revenue']:.2f}")
    print(f"  Ticket medio : ${result['average_order_value']:.2f}")
    print(f"  Por estado   : {result['orders_by_status']}")
    print(f"\n  Resumen en memoria: {repo.last_summary is not None}")


def demo_con_json() -> None:
    """LSP: exactamente el mismo OrderService, ahora con JSON en disco."""
    print("\n" + "=" * 60)
    print("2. CON JsonFileOrderRepository (data/orders.json)")
    print("=" * 60)

    repo = JsonFileOrderRepository(
        orders_path=Path("data") / "orders.json",
        summary_path=Path("data") / "output" / "solid_summary.json",
    )

    service = OrderService(repository=repo)
    result = service.process_orders(skip_invalid=True)

    print(f"\n  Válidas      : {result['valid_orders']}")
    print(f"  Inválidas    : {result['invalid_orders']}")
    print(f"  Revenue      : ${result['total_revenue']:.2f}")
    print(f"  Clientes     : {result['unique_customers']}")
    print(f"  Por estado   : {result['orders_by_status']}")
    print("\n  Resumen guardado en: data/output/solid_summary.json")


def demo_ocp_validador_personalizado() -> None:
    """OCP: validador nuevo sin modificar OrderService."""
    from order_management.services.order_validator import OrderValidator

    print("\n" + "=" * 60)
    print("3. OCP — Validador personalizado (rechaza @example.com)")
    print("=" * 60)

    class StrictValidator:
        def validate(self, order: dict[str, Any]) -> tuple[bool, str]:
            ok, msg = OrderValidator().validate(order)
            if not ok:
                return ok, msg
            email = order.get("email", "")
            if "@example.com" in email:
                return False, f"Dominio no permitido: {email}"
            return True, ""

    repo = InMemoryOrderRepository(
        orders=[
            {
                "order_id": "ORD-001",
                "customer_name": "Juan Pérez",
                "email": "juan.perez@example.com",  # ← será rechazado
                "status": "confirmed",
                "items": [{"product_name": "Laptop", "quantity": 1, "price": 999.0}],
            },
            {
                "order_id": "ORD-002",
                "customer_name": "Cliente Real",
                "email": "cliente@miempresa.mx",  # ← será aceptado
                "status": "pending",
                "items": [{"product_name": "Monitor", "quantity": 1, "price": 350.0}],
            },
        ]
    )

    service = OrderService(repository=repo, validator=StrictValidator())
    result = service.process_orders()

    print(f"\n  Válidas   : {result['valid_orders']}")
    print(f"  Inválidas : {result['invalid_orders']}")
    for inv in result["invalid_details"]:
        print(f"  ✗ {inv['order']['order_id']}: {inv['error']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MÓDULO 12: SOLID APLICADO EN PYTHON")
    print("SRP · OCP · LSP · ISP · DIP")
    print("=" * 60)

    demo_con_memoria()
    demo_con_json()
    demo_ocp_validador_personalizado()

    print("\n" + "=" * 60)
    print("✓ DEMO MÓDULO 12 COMPLETADO")
    print("=" * 60 + "\n")
