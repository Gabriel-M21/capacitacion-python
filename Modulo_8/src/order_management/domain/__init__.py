"""
Capa de dominio - Entidades de negocio
Usa dataclasses para representar el modelo de dominio puro
"""

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus

__all__ = [
    "Order",
    "OrderItem",
    "Customer",
    "Money",
    "Email",
    "OrderId",
    "OrderStatus",
]
