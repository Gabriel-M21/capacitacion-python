"""
Eventos de dominio - Módulo 16: Arquitectura Limpia

Los eventos de dominio representan hechos que ocurrieron en el dominio.
Son inmutables (frozen dataclasses) y no contienen lógica de negocio.

Regla de dependencia: los eventos viven en el dominio y NO importan
nada de infraestructura, aplicación ni frameworks.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """
    Clase base para todos los eventos de dominio.

    Atributos comunes a todo evento:
      - event_id:    identificador único del evento
      - occurred_at: momento en que ocurrió
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """
    Evento: se creó una nueva orden de compra.

    Publicado por CreateOrderUseCase al finalizar exitosamente.
    Puede ser manejado por:
      - NotificationHandler  → envía email/SMS al cliente
      - MetricsHandler       → actualiza dashboard de ventas
      - AuditHandler         → registra en log de auditoría
    """

    order_id: str = ""
    customer_email: str = ""
    customer_name: str = ""
    total: Decimal = Decimal("0")
    item_count: int = 0
    status: str = "pending"


@dataclass(frozen=True)
class OrderStatusChanged(DomainEvent):
    """
    Evento: el estado de una orden cambió.

    Publicado cuando se llama a order.change_status().
    """

    order_id: str = ""
    old_status: str = ""
    new_status: str = ""


@dataclass(frozen=True)
class OrderItemAdded(DomainEvent):
    """
    Evento: se agregó un item a una orden existente.
    """

    order_id: str = ""
    product_name: str = ""
    quantity: int = 0
    unit_price: Decimal = Decimal("0")
