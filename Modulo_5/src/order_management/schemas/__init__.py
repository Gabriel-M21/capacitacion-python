"""
Capa de API - Schemas de entrada/salida
Usa Pydantic para validación y serialización
"""

from order_management.schemas.schemas import (
    CustomerIn,
    CustomerOut,
    OrderIn,
    OrderItemIn,
    OrderItemOut,
    OrderOut,
)

__all__ = [
    "OrderIn",
    "OrderOut",
    "OrderItemIn",
    "OrderItemOut",
    "CustomerIn",
    "CustomerOut",
]
