"""
Value Objects - Objetos inmutables que representan valores del dominio
Módulo 4: Objetos y modelos de datos
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    """Estados posibles de una orden (Enum inmutable)"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    def can_transition_to(self, new_status: "OrderStatus") -> bool:
        """
        Valida si es posible transicionar al nuevo estado.

        Args:
            new_status: Estado destino

        Returns:
            True si la transición es válida
        """
        valid_transitions = {
            OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
            OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
            OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
            OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
            OrderStatus.DELIVERED: set(),
            OrderStatus.CANCELLED: set(),
        }
        return new_status in valid_transitions.get(self, set())


@dataclass(frozen=True)
class Money:
    """
    Value Object para representar dinero (inmutable).

    Attributes:
        amount: Cantidad en Decimal
        currency: Código de moneda (ISO 4217)
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validación después de inicialización."""
        if self.amount < 0:
            raise ValueError(f"El monto no puede ser negativo: {self.amount}")

        if len(self.currency) != 3:
            raise ValueError(f"Código de moneda inválido: {self.currency}")

    def __str__(self) -> str:
        """Representación en string."""
        return f"{self.currency} {self.amount:.2f}"

    def __add__(self, other: "Money") -> "Money":
        """Suma de Money."""
        if self.currency != other.currency:
            raise ValueError(
                f"No se pueden sumar monedas diferentes: {self.currency} != {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Resta de Money."""
        if self.currency != other.currency:
            raise ValueError(
                f"No se pueden restar monedas diferentes: {self.currency} != {other.currency}"
            )
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money":
        """Multiplicación por escalar."""
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __lt__(self, other: "Money") -> bool:
        """Comparación menor que."""
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        """Comparación menor o igual que."""
        if self.currency != other.currency:
            raise ValueError("No se pueden comparar monedas diferentes")
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        """Comparación mayor que."""
        return not self <= other

    def __ge__(self, other: "Money") -> bool:
        """Comparación mayor o igual que."""
        return not self < other

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        """Crea un Money con valor cero."""
        return cls(Decimal("0"), currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> "Money":
        """Crea Money desde float (convierte a Decimal)."""
        return cls(Decimal(str(amount)), currency)


@dataclass(frozen=True)
class Email:
    """
    Value Object para email (inmutable con validación).

    Attributes:
        address: Dirección de email
    """

    address: str

    def __post_init__(self) -> None:
        """Valida el formato del email."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, self.address):
            raise ValueError(f"Email inválido: {self.address}")

    def __str__(self) -> str:
        """Representación en string."""
        return self.address

    @property
    def domain(self) -> str:
        """Extrae el dominio del email."""
        return self.address.split("@")[1]


@dataclass(frozen=True)
class OrderId:
    """
    Value Object para ID de orden (inmutable con formato).

    Attributes:
        value: Valor del ID (formato: ORD-XXXXX)
    """

    value: str

    def __post_init__(self) -> None:
        """Valida el formato del ID."""
        if not re.match(r"^ORD-\d{3,}$", self.value):
            raise ValueError(f"Formato de OrderId inválido: {self.value}")

    def __str__(self) -> str:
        """Representación en string."""
        return self.value

    def __hash__(self) -> int:
        """Hash para usar en sets/dicts."""
        return hash(self.value)

    @classmethod
    def generate(cls, sequence: int) -> "OrderId":
        """Genera un OrderId desde un número de secuencia."""
        return cls(f"ORD-{sequence:05d}")
