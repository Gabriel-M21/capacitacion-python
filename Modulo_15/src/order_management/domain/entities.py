"""
Entidades de dominio - Módulo 4: Objetos y modelos de datos
Usa dataclasses para modelar entidades con comportamiento
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus


@dataclass
class OrderItem:
    """
    Item de una orden con cálculos derivados.

    Attributes:
        product_name: Nombre del producto
        quantity: Cantidad
        unit_price: Precio unitario
    """

    product_name: str
    quantity: int
    unit_price: Money

    def __post_init__(self) -> None:
        """Validación post-inicialización."""
        if not self.product_name or not self.product_name.strip():
            raise ValueError("product_name no puede estar vacío")

        if self.quantity <= 0:
            raise ValueError(f"quantity debe ser mayor a 0: {self.quantity}")

        if self.unit_price.amount <= 0:
            raise ValueError(f"unit_price debe ser mayor a 0: {self.unit_price}")

    @property
    def subtotal(self) -> Money:
        """Calcula el subtotal (quantity * unit_price)."""
        return self.unit_price * self.quantity

    def __str__(self) -> str:
        """Representación en string."""
        return f"{self.quantity}x {self.product_name} @ {self.unit_price} = {self.subtotal}"

    def __repr__(self) -> str:
        """Representación para debugging."""
        return (
            f"OrderItem(product_name='{self.product_name}', "
            f"quantity={self.quantity}, unit_price={self.unit_price})"
        )


@dataclass
class Customer:
    """
    Cliente con información de contacto.

    Attributes:
        name: Nombre del cliente
        email: Email del cliente
        phone: Teléfono (opcional)
    """

    name: str
    email: Email
    phone: str | None = None

    def __post_init__(self) -> None:
        """Validación post-inicialización."""
        if not self.name or not self.name.strip():
            raise ValueError("name no puede estar vacío")

    def __str__(self) -> str:
        """Representación en string."""
        return f"{self.name} <{self.email}>"

    def __repr__(self) -> str:
        """Representación para debugging."""
        return f"Customer(name='{self.name}', email={self.email!r})"


@dataclass
class Order:
    """
    Orden de compra con comportamiento y cálculos derivados.

    Attributes:
        order_id: ID único de la orden
        customer: Cliente que realiza la orden
        items: Lista de items
        status: Estado actual
        created_at: Fecha de creación
        notes: Notas adicionales (opcional)
    """

    order_id: OrderId
    customer: Customer
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validación post-inicialización."""
        if not self.items:
            raise ValueError("La orden debe tener al menos un item")

        # Validar que todas las monedas sean iguales
        currencies = {item.unit_price.currency for item in self.items}
        if len(currencies) > 1:
            raise ValueError(f"Todos los items deben usar la misma moneda: {currencies}")

    @property
    def total(self) -> Money:
        """Calcula el total de la orden."""
        if not self.items:
            return Money.zero()

        currency = self.items[0].unit_price.currency
        total_amount = sum((item.subtotal.amount for item in self.items), Decimal("0"))
        return Money(total_amount, currency)

    @property
    def item_count(self) -> int:
        """Cuenta el total de items (suma de cantidades)."""
        return sum(item.quantity for item in self.items)

    @property
    def product_count(self) -> int:
        """Cuenta el número de productos distintos."""
        return len(self.items)

    def add_item(self, item: OrderItem) -> None:
        """
        Agrega un item a la orden.

        Args:
            item: Item a agregar

        Raises:
            ValueError: Si la orden no está en estado PENDING
        """
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"No se pueden agregar items en estado {self.status}")

        # Validar moneda
        if self.items and item.unit_price.currency != self.items[0].unit_price.currency:
            raise ValueError("El item debe usar la misma moneda que la orden")

        self.items.append(item)

    def remove_item(self, product_name: str) -> bool:
        """
        Elimina un item por nombre de producto.

        Args:
            product_name: Nombre del producto a eliminar

        Returns:
            True si se eliminó, False si no se encontró

        Raises:
            ValueError: Si la orden no está en estado PENDING
        """
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"No se pueden eliminar items en estado {self.status}")

        initial_count = len(self.items)
        self.items = [item for item in self.items if item.product_name != product_name]
        return len(self.items) < initial_count

    def change_status(self, new_status: OrderStatus) -> None:
        """
        Cambia el estado de la orden con validación.

        Args:
            new_status: Nuevo estado

        Raises:
            ValueError: Si la transición no es válida
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(f"Transición inválida: {self.status.value} -> {new_status.value}")
        self.status = new_status

    def apply_discount(self, percentage: Decimal) -> Money:
        """
        Calcula el total con descuento.

        Args:
            percentage: Porcentaje de descuento (0-100)

        Returns:
            Total después del descuento

        Raises:
            ValueError: Si el porcentaje es inválido
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Porcentaje debe estar entre 0 y 100: {percentage}")

        discount_factor = Decimal("1") - (percentage / Decimal("100"))
        return self.total * discount_factor

    def __str__(self) -> str:
        """Representación en string."""
        return (
            f"Order {self.order_id} - {self.customer.name} - "
            f"{self.product_count} productos - Total: {self.total} - Status: {self.status.value}"
        )

    def __repr__(self) -> str:
        """Representación para debugging."""
        return (
            f"Order(order_id={self.order_id!r}, customer={self.customer!r}, "
            f"items={len(self.items)}, status={self.status!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Igualdad basada en order_id."""
        if not isinstance(other, Order):
            return NotImplemented
        return self.order_id == other.order_id

    def __hash__(self) -> int:
        """Hash basado en order_id."""
        return hash(self.order_id)

    def __lt__(self, other: "Order") -> bool:
        """Comparación por total (para ordenamiento)."""
        return self.total < other.total

    def __le__(self, other: "Order") -> bool:
        """Comparación menor o igual."""
        return self.total <= other.total
