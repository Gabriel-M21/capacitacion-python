"""
Builder de órdenes - Módulo 13: Patrones de diseño
Patrón: Builder

Construye objetos Order complejos paso a paso, evitando constructores
con demasiados parámetros y garantizando que el objeto final sea válido.
"""

from datetime import datetime
from decimal import Decimal

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus


class OrderBuildError(Exception):
    """Se lanza cuando el Builder intenta construir una orden inválida."""


class OrderBuilder:
    """
    Construye objetos Order paso a paso.

    Builder: separa la construcción de la representación.
    Cada método retorna self para permitir encadenamiento fluido.

    Example:
        order = (
            OrderBuilder(order_id=OrderId.generate(1))
            .with_customer("Juan Pérez", "juan@example.com")
            .add_item("Laptop", quantity=1, unit_price=1299.99)
            .add_item("Mouse", quantity=2, unit_price=29.99)
            .with_notes("Entrega urgente")
            .build()
        )
    """

    def __init__(self, order_id: OrderId) -> None:
        self._order_id: OrderId = order_id
        self._customer: Customer | None = None
        self._items: list[OrderItem] = []
        self._status: OrderStatus = OrderStatus.PENDING
        self._created_at: datetime = datetime.now()
        self._notes: str | None = None

    # ------------------------------------------------------------------
    # Pasos de construcción
    # ------------------------------------------------------------------

    def with_customer(
        self,
        name: str,
        email: str,
        phone: str | None = None,
    ) -> "OrderBuilder":
        """
        Establece el cliente de la orden.

        Args:
            name:  Nombre completo
            email: Email válido
            phone: Teléfono opcional
        """
        self._customer = Customer(
            name=name,
            email=Email(email),
            phone=phone,
        )
        return self

    def add_item(
        self,
        product_name: str,
        quantity: int,
        unit_price: float | Decimal,
        currency: str = "USD",
    ) -> "OrderBuilder":
        """
        Añade un item a la orden.

        Args:
            product_name: Nombre del producto
            quantity:     Cantidad (> 0)
            unit_price:   Precio unitario (> 0)
            currency:     Código ISO 4217 (default USD)
        """
        self._items.append(
            OrderItem(
                product_name=product_name,
                quantity=quantity,
                unit_price=Money(
                    amount=Decimal(str(unit_price)),
                    currency=currency,
                ),
            )
        )
        return self

    def with_status(self, status: OrderStatus) -> "OrderBuilder":
        """Establece el estado inicial de la orden."""
        self._status = status
        return self

    def with_notes(self, notes: str) -> "OrderBuilder":
        """Añade notas a la orden."""
        self._notes = notes
        return self

    def with_created_at(self, created_at: datetime) -> "OrderBuilder":
        """Establece la fecha de creación (útil en tests y migraciones)."""
        self._created_at = created_at
        return self

    # ------------------------------------------------------------------
    # Construcción final
    # ------------------------------------------------------------------

    def build(self) -> Order:
        """
        Construye y valida la Order.

        Returns:
            Order completamente construida

        Raises:
            OrderBuildError: Si faltan datos obligatorios
        """
        if self._customer is None:
            raise OrderBuildError("Se requiere un cliente. Usa .with_customer() antes de .build()")
        if not self._items:
            raise OrderBuildError("Se requiere al menos un item. Usa .add_item() antes de .build()")

        return Order(
            order_id=self._order_id,
            customer=self._customer,
            items=list(self._items),
            status=self._status,
            created_at=self._created_at,
            notes=self._notes,
        )

    # ------------------------------------------------------------------
    # Factory methods — constructores semánticos (variante del patrón)
    # ------------------------------------------------------------------

    @classmethod
    def express_order(
        cls,
        order_id: OrderId,
        customer_name: str,
        customer_email: str,
    ) -> "OrderBuilder":
        """
        Factory method: crea un builder preconfigurado para órdenes express.
        Las órdenes express nacen en estado CONFIRMED con nota automática.
        """
        return (
            cls(order_id=order_id)
            .with_customer(customer_name, customer_email)
            .with_status(OrderStatus.CONFIRMED)
            .with_notes("Orden express — procesamiento prioritario")
        )
