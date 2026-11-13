"""
Mapper para conversión entre Domain y API - Módulo 4
"""

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus
from order_management.schemas.schemas import (
    CustomerIn,
    CustomerOut,
    OrderIn,
    OrderItemIn,
    OrderItemOut,
    OrderOut,
)


class OrderMapper:
    """Convierte entre entidades de dominio y schemas de API."""

    @staticmethod
    def to_domain_item(item_in: OrderItemIn, currency: str = "USD") -> OrderItem:
        """
        Convierte OrderItemIn (API) a OrderItem (Domain).

        Args:
            item_in: Schema de entrada
            currency: Código de moneda

        Returns:
            Entidad de dominio
        """
        return OrderItem(
            product_name=item_in.product_name,
            quantity=item_in.quantity,
            unit_price=Money(item_in.unit_price, currency),
        )

    @staticmethod
    def to_api_item(item: OrderItem) -> OrderItemOut:
        """
        Convierte OrderItem (Domain) a OrderItemOut (API).

        Args:
            item: Entidad de dominio

        Returns:
            Schema de salida
        """
        return OrderItemOut(
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price.amount,
            subtotal=item.subtotal.amount,
        )

    @staticmethod
    def to_domain_customer(customer_in: CustomerIn) -> Customer:
        """
        Convierte CustomerIn (API) a Customer (Domain).

        Args:
            customer_in: Schema de entrada

        Returns:
            Entidad de dominio
        """
        return Customer(
            name=customer_in.name,
            email=Email(customer_in.email),
            phone=customer_in.phone,
        )

    @staticmethod
    def to_api_customer(customer: Customer) -> CustomerOut:
        """
        Convierte Customer (Domain) a CustomerOut (API).

        Args:
            customer: Entidad de dominio

        Returns:
            Schema de salida
        """
        return CustomerOut(name=customer.name, email=str(customer.email), phone=customer.phone)

    @staticmethod
    def to_domain_order(order_in: OrderIn, order_id: OrderId) -> Order:
        """
        Convierte OrderIn (API) a Order (Domain).

        Args:
            order_in: Schema de entrada
            order_id: ID generado para la orden

        Returns:
            Entidad de dominio
        """
        customer = OrderMapper.to_domain_customer(order_in.customer)
        items = [OrderMapper.to_domain_item(item) for item in order_in.items]

        return Order(
            order_id=order_id,
            customer=customer,
            items=items,
            status=OrderStatus.PENDING,
            notes=order_in.notes,
        )

    @staticmethod
    def to_api_order(order: Order) -> OrderOut:
        """
        Convierte Order (Domain) a OrderOut (API).

        Args:
            order: Entidad de dominio

        Returns:
            Schema de salida
        """
        return OrderOut(
            order_id=str(order.order_id),
            customer=OrderMapper.to_api_customer(order.customer),
            items=[OrderMapper.to_api_item(item) for item in order.items],
            status=order.status.value,
            total=order.total.amount,
            item_count=order.item_count,
            product_count=order.product_count,
            created_at=order.created_at,
            notes=order.notes,
        )
