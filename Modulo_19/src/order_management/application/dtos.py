"""
DTOs de aplicación - Módulo 15: Arquitectura Hexagonal

Los DTOs (Data Transfer Objects) de aplicación son distintos de los schemas
de API (OrderIn/OrderOut del Módulo 4):
  - Los schemas de API validan y serializan datos HTTP
  - Los DTOs de aplicación comunican casos de uso con el exterior
    sin acoplar el dominio a Pydantic ni a FastAPI

Esto permite usar los casos de uso desde CLI, tests, workers, etc.
sin necesitar un contexto HTTP.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderItemCommand:
    """Item individual dentro de un comando de creación de orden."""

    product_name: str
    quantity: int
    unit_price: Decimal
    currency: str = "USD"


@dataclass(frozen=True)
class CreateOrderCommand:
    """
    Comando para el caso de uso CreateOrder.

    Contiene todos los datos necesarios para crear una orden.
    Inmutable (frozen=True) para garantizar que no se modifica
    durante la ejecución del caso de uso.
    """

    customer_name: str
    customer_email: str
    items: list[OrderItemCommand]
    notes: str | None = None
    customer_phone: str | None = None
    sequence_number: int = 1

    def __post_init__(self) -> None:
        if not self.customer_name.strip():
            raise ValueError("customer_name no puede estar vacío")
        if not self.customer_email.strip():
            raise ValueError("customer_email no puede estar vacío")
        if not self.items:
            raise ValueError("La orden debe tener al menos un item")


@dataclass(frozen=True)
class OrderItemResult:
    """Item dentro del resultado de creación de orden."""

    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    currency: str


@dataclass(frozen=True)
class OrderCreatedResult:
    """
    Resultado del caso de uso CreateOrder.

    Contiene la información necesaria para confirmar al cliente
    que su orden fue creada y para enrutar notificaciones.
    """

    order_id: str
    customer_name: str
    customer_email: str
    status: str
    total: Decimal
    items: list[OrderItemResult]
    notes: str | None = None

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def total_float(self) -> float:
        return float(self.total)
