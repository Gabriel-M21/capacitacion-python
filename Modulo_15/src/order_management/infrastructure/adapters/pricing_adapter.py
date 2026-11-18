"""
Adapter de precios externo - Módulo 13: Patrones de diseño
Patrón: Adapter

Adapta una API externa hipotética de precios al Protocol PricingStrategy,
sin modificar ni la API externa ni PricingStrategy.
"""

from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------------------
# API externa simulada (no controlada por nosotros)
# ---------------------------------------------------------------------------


class ExternalPricingAPI:
    """
    Simula una API externa de precios con una interfaz distinta a la nuestra.
    En producción sería un cliente HTTP real (como CatalogClient).

    Interfaz externa — NO implementa PricingStrategy.
    """

    def get_discount_rate(
        self,
        customer_tier: str,
        item_count: int,
        total_amount: float,
    ) -> float:
        """
        Devuelve la tasa de descuento como float (0.0 - 1.0).
        Interfaz completamente distinta a calculate_discount().
        """
        # Lógica simulada de la API externa
        if customer_tier == "GOLD" and total_amount > 500:
            return 0.20
        if customer_tier == "SILVER" and item_count >= 3:
            return 0.10
        if total_amount > 1000:
            return 0.05
        return 0.0


# ---------------------------------------------------------------------------
# Adapter — traduce ExternalPricingAPI → PricingStrategy
# ---------------------------------------------------------------------------


class ExternalPricingAdapter:
    """
    Adapta ExternalPricingAPI al Protocol PricingStrategy.

    Adapter: convierte la interfaz de una clase en otra que el cliente espera.
    OrderService no sabe que está usando una API externa — solo ve
    un objeto que cumple PricingStrategy.
    """

    # Mapeo de emails a tiers (en producción vendría de la DB)
    _TIER_BY_EMAIL: dict[str, str] = {
        "admin@example.com": "GOLD",
        "laura.gomez@example.com": "GOLD",
        "juan.perez@example.com": "SILVER",
        "maria.garcia@example.com": "SILVER",
    }

    def __init__(self, api: ExternalPricingAPI | None = None) -> None:
        self._api = api or ExternalPricingAPI()

    def calculate_discount(self, order: dict[str, Any]) -> Decimal:
        """
        Implementa PricingStrategy usando ExternalPricingAPI internamente.

        Traduce:
          - order["email"]  → customer_tier
          - len(items)      → item_count
          - sum(prices)     → total_amount
          - float (0-1)     → Decimal (0-100)
        """
        email = str(order.get("email", "")).lower()
        tier = self._TIER_BY_EMAIL.get(email, "STANDARD")

        items = order.get("items", [])
        item_count = len(items)
        total_amount = sum(float(i.get("price", 0)) * float(i.get("quantity", 1)) for i in items)

        # Llamada a la API externa con su interfaz propia
        rate = self._api.get_discount_rate(
            customer_tier=tier,
            item_count=item_count,
            total_amount=total_amount,
        )

        # Traducción: float 0-1 → Decimal 0-100
        return Decimal(str(round(rate * 100, 2)))
