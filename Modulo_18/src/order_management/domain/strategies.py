"""
Estrategias de precios - Módulo 13: Patrones de diseño
Patrón: Strategy

Permite intercambiar algoritmos de descuento sin modificar OrderService.
Cada estrategia implementa PricingStrategy (Protocol) — DIP del Módulo 12.
"""

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from order_management.domain.pricing import volume_discount

# ---------------------------------------------------------------------------
# Puerto — Strategy Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PricingStrategy(Protocol):
    """
    Contrato para cualquier estrategia de descuento.

    Strategy: define una familia de algoritmos intercambiables.
    Los clientes (OrderService) trabajan con este Protocol,
    no con implementaciones concretas.
    """

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        """
        Calcula el porcentaje de descuento para una orden.

        Args:
            order: Diccionario con datos de la orden (incluye 'items')

        Returns:
            Porcentaje de descuento como Decimal (0-100)
        """
        ...


# ---------------------------------------------------------------------------
# Estrategia 1 — Sin descuento (baseline / Null Object)
# ---------------------------------------------------------------------------


class NoDiscountStrategy:
    """
    Estrategia nula: nunca aplica descuento.
    Útil como valor por defecto y para comparación en benchmarks.
    """

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        return Decimal("0")


# ---------------------------------------------------------------------------
# Estrategia 2 — Descuento por volumen (reutiliza Módulo 10)
# ---------------------------------------------------------------------------


class VolumeDiscountStrategy:
    """
    Descuento según número de items de la orden.
    Delega en volume_discount() del Módulo 10:
      1-2 items → 0%, 3-5 → 5%, 6-9 → 10%, 10+ → 15%
    """

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        item_count = sum(int(item.get("quantity", 1)) for item in order.get("items", []))
        return volume_discount(max(item_count, 1))


# ---------------------------------------------------------------------------
# Estrategia 3 — Descuento de temporada (fijo, configurable)
# ---------------------------------------------------------------------------


class SeasonalDiscountStrategy:
    """
    Descuento fijo aplicado durante una temporada o promoción.

    OCP: añadir una nueva temporada no modifica otras estrategias.
    """

    def __init__(self, discount_percentage: Decimal = Decimal("10")) -> None:
        """
        Args:
            discount_percentage: Porcentaje fijo a aplicar (0-100)
        """
        if not Decimal("0") <= discount_percentage <= Decimal("100"):
            raise ValueError(f"El descuento debe estar entre 0 y 100: {discount_percentage}")
        self._discount = discount_percentage

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        return self._discount


# ---------------------------------------------------------------------------
# Estrategia 4 — Descuento por cliente VIP
# ---------------------------------------------------------------------------


class VIPDiscountStrategy:
    """
    Aplica descuento solo si el cliente está en la lista VIP.
    Si no está, cae back al descuento por volumen.
    """

    def __init__(
        self,
        vip_emails: set[str],
        vip_discount: Decimal = Decimal("20"),
    ) -> None:
        self._vip_emails = {e.lower() for e in vip_emails}
        self._vip_discount = vip_discount
        self._fallback = VolumeDiscountStrategy()

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        email = str(order.get("email", "")).lower()
        if email in self._vip_emails:
            return self._vip_discount
        return self._fallback.calculate_discount(order)


# ---------------------------------------------------------------------------
# Estrategia 5 — Descuento compuesto (máximo entre varias estrategias)
# ---------------------------------------------------------------------------


class MaxDiscountStrategy:
    """
    Aplica el máximo descuento entre varias estrategias.
    Patrón Composite aplicado sobre Strategy.
    """

    def __init__(self, strategies: list[PricingStrategy]) -> None:
        if not strategies:
            raise ValueError("Se requiere al menos una estrategia")
        self._strategies = strategies

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        return max(s.calculate_discount(order) for s in self._strategies)
