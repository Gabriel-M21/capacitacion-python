"""
Presenters - Módulo 16: Arquitectura Limpia

El Presenter traduce el resultado interno de un caso de uso
al formato que necesita cada canal de salida (API, CLI, JSON, etc.).

Regla de dependencia:
  - El caso de uso devuelve un DTO interno (OrderCreatedResult)
  - El Presenter lo convierte al formato del canal de salida
  - El caso de uso NO sabe nada del formato de salida

Esto permite que el mismo caso de uso sirva a:
  - Una API REST (JSON)
  - Una CLI (texto formateado)
  - Un test (dict Python)
  - Un webhook (payload específico)
"""

from typing import Any, Protocol, runtime_checkable

from order_management.application.dtos import OrderCreatedResult
from order_management.schemas.schemas import CustomerOut, OrderItemOut, OrderOut


@runtime_checkable
class OrderPresenterPort(Protocol):
    """
    Puerto del Presenter para órdenes creadas.

    Cualquier clase con un método present() cumple este contrato.
    """

    def present(self, result: OrderCreatedResult) -> Any:
        """
        Transforma OrderCreatedResult al formato de salida.

        Args:
            result: DTO interno del caso de uso

        Returns:
            Representación en el formato del canal (dict, str, schema, etc.)
        """
        ...


# ---------------------------------------------------------------------------
# Presenter 1 — JSON / dict (para APIs, webhooks, tests)
# ---------------------------------------------------------------------------


class JsonPresenter:
    """
    Convierte OrderCreatedResult a dict serializable como JSON.
    Útil para APIs REST, webhooks y tests de integración.
    """

    def present(self, result: OrderCreatedResult) -> dict[str, Any]:
        return {
            "order_id": result.order_id,
            "customer_name": result.customer_name,
            "customer_email": result.customer_email,
            "status": result.status,
            "total": float(result.total),
            "item_count": result.item_count,
            "items": [
                {
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "subtotal": float(item.subtotal),
                    "currency": item.currency,
                }
                for item in result.items
            ],
            "notes": result.notes,
        }


# ---------------------------------------------------------------------------
# Presenter 2 — CLI / texto formateado
# ---------------------------------------------------------------------------


class CliPresenter:
    """
    Convierte OrderCreatedResult a texto legible para terminal.
    Útil para scripts CLI y demos.
    """

    def present(self, result: OrderCreatedResult) -> str:
        lines = [
            "✓ Orden creada exitosamente",
            f"  ID       : {result.order_id}",
            f"  Cliente  : {result.customer_name} <{result.customer_email}>",
            f"  Estado   : {result.status}",
            f"  Items    : {result.item_count}",
        ]
        for item in result.items:
            lines.append(
                f"    • {item.product_name:<35} " f"x{item.quantity}  ${item.subtotal:.2f}"
            )
        lines.append(f"  Total    : ${result.total:.2f} {result.items[0].currency}")
        if result.notes:
            lines.append(f"  Notas    : {result.notes}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Presenter 3 — FastAPI / Pydantic schema (OrderOut)
# ---------------------------------------------------------------------------


class ApiPresenter:
    """
    Convierte OrderCreatedResult al schema Pydantic OrderOut.
    Permite que el router de FastAPI devuelva el schema existente
    sin acoplar el caso de uso a Pydantic.
    """

    def present(self, result: OrderCreatedResult) -> OrderOut:
        from datetime import datetime

        return OrderOut(
            order_id=result.order_id,
            customer=CustomerOut(
                name=result.customer_name,
                email=result.customer_email,
            ),
            items=[
                OrderItemOut(
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
                for item in result.items
            ],
            status=result.status,
            total=result.total,
            item_count=result.item_count,
            product_count=result.item_count,
            created_at=datetime.now(),
            notes=result.notes,
        )


# ---------------------------------------------------------------------------
# Presenter 4 — Auditoría (payload mínimo para log de auditoría)
# ---------------------------------------------------------------------------


class AuditPresenter:
    """
    Genera un payload mínimo para registro de auditoría.
    Solo incluye los campos necesarios para trazabilidad.
    """

    def present(self, result: OrderCreatedResult) -> dict[str, Any]:
        return {
            "event": "ORDER_CREATED",
            "order_id": result.order_id,
            "customer_email": result.customer_email,
            "total": str(result.total),
            "item_count": result.item_count,
            "status": result.status,
        }
