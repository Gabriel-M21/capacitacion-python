"""
Schemas Pydantic para validación y serialización - Módulo 4
Representa contratos de entrada/salida de la API
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CatalogProductOut(BaseModel):
    """Producto recibido del servicio externo de catálogo."""

    product_id: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1, max_length=200)
    unit_price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    available: bool


class OrderItemIn(BaseModel):
    """Schema de entrada para crear un item de orden."""

    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0, description="Cantidad debe ser mayor a 0")
    unit_price: Decimal = Field(..., gt=0, description="Precio debe ser mayor a 0")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Laptop Dell XPS 15",
                "quantity": 1,
                "unit_price": 1299.99,
            }
        }
    )


class OrderItemOut(BaseModel):
    """Schema de salida para un item de orden (incluye subtotal)."""

    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_name": "Laptop Dell XPS 15",
                "quantity": 1,
                "unit_price": 1299.99,
                "subtotal": 1299.99,
            }
        }
    )


class CustomerIn(BaseModel):
    """Schema de entrada para crear un cliente."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Juan Pérez",
                "email": "juan.perez@example.com",
                "phone": "+52 55 1234 5678",
            }
        }
    )


class CustomerOut(BaseModel):
    """Schema de salida para un cliente."""

    name: str
    email: str
    phone: str | None = None


class OrderIn(BaseModel):
    """Schema de entrada para crear una orden."""

    customer: CustomerIn
    items: list[OrderItemIn] = Field(..., min_length=1)
    notes: str | None = Field(None, max_length=500)

    @field_validator("items")
    @classmethod
    def validate_items_not_empty(cls, v: list[OrderItemIn]) -> list[OrderItemIn]:
        """Valida que la lista de items no esté vacía."""
        if not v:
            raise ValueError("La orden debe tener al menos un item")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer": {
                    "name": "Juan Pérez",
                    "email": "juan.perez@example.com",
                    "phone": "+52 55 1234 5678",
                },
                "items": [
                    {"product_name": "Laptop Dell XPS 15", "quantity": 1, "unit_price": 1299.99},
                    {"product_name": "Mouse Logitech", "quantity": 2, "unit_price": 29.99},
                ],
                "notes": "Entrega urgente",
            }
        }
    )


class OrderOut(BaseModel):
    """Schema de salida para una orden (incluye cálculos derivados)."""

    order_id: str
    customer: CustomerOut
    items: list[OrderItemOut]
    status: str
    total: Decimal
    item_count: int
    product_count: int
    created_at: datetime
    notes: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_id": "ORD-00001",
                "customer": {
                    "name": "Juan Pérez",
                    "email": "juan.perez@example.com",
                    "phone": "+52 55 1234 5678",
                },
                "items": [
                    {
                        "product_name": "Laptop Dell XPS 15",
                        "quantity": 1,
                        "unit_price": 1299.99,
                        "subtotal": 1299.99,
                    }
                ],
                "status": "pending",
                "total": 1299.99,
                "item_count": 1,
                "product_count": 1,
                "created_at": "2024-01-15T10:30:00",
                "notes": "Entrega urgente",
            }
        }
    )
