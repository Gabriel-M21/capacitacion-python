"""
Demo del Módulo 13: Patrones de diseño en acción
Strategy · Builder · Adapter · Decorator
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

from order_management.clients.cached_catalog_client import CachedCatalogClient
from order_management.domain.strategies import (
    MaxDiscountStrategy,
    NoDiscountStrategy,
    SeasonalDiscountStrategy,
    VIPDiscountStrategy,
    VolumeDiscountStrategy,
)
from order_management.domain.value_objects import OrderId
from order_management.infrastructure.adapters.pricing_adapter import ExternalPricingAdapter
from order_management.schemas.schemas import CatalogProductOut
from order_management.services.order_builder import OrderBuilder

# ---------------------------------------------------------------------------
# Orden de ejemplo compartida
# ---------------------------------------------------------------------------

SAMPLE_ORDER = {
    "order_id": "ORD-001",
    "email": "laura.gomez@example.com",
    "items": [
        {"product_name": "Laptop Dell XPS 15", "quantity": 1, "price": 1299.99},
        {"product_name": "Mouse Logitech", "quantity": 2, "price": 29.99},
        {"product_name": "Teclado mecánico", "quantity": 1, "price": 129.50},
        {"product_name": "Monitor 4K", "quantity": 1, "price": 599.00},
        {"product_name": "Webcam Logitech", "quantity": 1, "price": 89.99},
        {"product_name": "Auriculares Sony", "quantity": 1, "price": 349.99},
    ],
}


# ---------------------------------------------------------------------------
# STRATEGY
# ---------------------------------------------------------------------------


def demo_strategy() -> None:
    print("\n" + "=" * 60)
    print("1. STRATEGY — Estrategias de descuento intercambiables")
    print("=" * 60)
    from order_management.domain.strategies import PricingStrategy

    strategies: dict[str, PricingStrategy] = {
        "Sin descuento": NoDiscountStrategy(),
        "Por volumen": VolumeDiscountStrategy(),
        "Temporada (12%)": SeasonalDiscountStrategy(Decimal("12")),
        "VIP (Laura)": VIPDiscountStrategy(
            vip_emails={"laura.gomez@example.com"},
            vip_discount=Decimal("20"),
        ),
        "Máximo": MaxDiscountStrategy(
            [
                VolumeDiscountStrategy(),
                SeasonalDiscountStrategy(Decimal("12")),
                VIPDiscountStrategy(
                    {"laura.gomez@example.com"},
                    Decimal("20"),
                ),
            ]
        ),
        "Adapter externo": ExternalPricingAdapter(),
    }

    items: list[dict[str, object]] = SAMPLE_ORDER["items"]  # type: ignore[assignment]
    total: float = sum(float(str(i["price"])) * float(str(i["quantity"])) for i in items)

    print(f"\n  Total bruto: ${total:.2f}")
    print(f"\n  {'Estrategia':<22} {'Descuento':>10}  {'Total final':>12}")
    print("  " + "-" * 48)

    for name, strategy in strategies.items():
        pct = strategy.calculate_discount(SAMPLE_ORDER)
        factor = (Decimal("100") - pct) / Decimal("100")
        final = Decimal(str(total)) * factor
        print(f"  {name:<22} {pct:>9.0f}%  ${final:>11.2f}")


# ---------------------------------------------------------------------------
# BUILDER
# ---------------------------------------------------------------------------


def demo_builder() -> None:
    print("\n" + "=" * 60)
    print("2. BUILDER — Construcción fluida de órdenes")
    print("=" * 60)

    # Orden normal
    order = (
        OrderBuilder(order_id=OrderId.generate(1))
        .with_customer("Juan Pérez", "juan.perez@example.com", "+52 55 1234")
        .add_item("Laptop Dell XPS 15", quantity=1, unit_price=1299.99)
        .add_item("Mouse Logitech MX Master", quantity=2, unit_price=29.99)
        .with_notes("Entrega urgente")
        .build()
    )

    print("\n  Orden normal:")
    print(f"    ID       : {order.order_id}")
    print(f"    Cliente  : {order.customer.name}")
    print(f"    Items    : {order.product_count}")
    print(f"    Total    : {order.total}")
    print(f"    Estado   : {order.status.value}")
    print(f"    Notas    : {order.notes}")

    # Orden express (factory method)
    express = (
        OrderBuilder.express_order(
            order_id=OrderId.generate(99),
            customer_name="Laura Gómez",
            customer_email="laura.gomez@example.com",
        )
        .add_item("MacBook Air M3", quantity=1, unit_price=1299.99)
        .add_item("Magic Mouse", quantity=1, unit_price=79.00)
        .build()
    )

    print("\n  Orden express (factory method):")
    print(f"    ID       : {express.order_id}")
    print(f"    Estado   : {express.status.value}  ← nace CONFIRMED")
    print(f"    Total    : {express.total}")
    print(f"    Notas    : {express.notes}")


# ---------------------------------------------------------------------------
# ADAPTER
# ---------------------------------------------------------------------------


def demo_adapter() -> None:
    print("\n" + "=" * 60)
    print("3. ADAPTER — API externa adaptada a PricingStrategy")
    print("=" * 60)

    adapter = ExternalPricingAdapter()

    cases = [
        {"label": "Laura Gómez (GOLD)", "email": "laura.gomez@example.com", "total": 600.0},
        {"label": "Juan Pérez (SILVER)", "email": "juan.perez@example.com", "total": 300.0},
        {"label": "Desconocido (ninguno)", "email": "nuevo@empresa.mx", "total": 50.0},
    ]

    print(f"\n  {'Cliente':<28} {'Descuento':>10}")
    print("  " + "-" * 40)

    for case in cases:
        order = {
            "email": case["email"],
            "items": [
                {"product_name": "Producto", "quantity": 3, "price": float(str(case["total"])) / 3}
            ],
        }
        discount = adapter.calculate_discount(order)
        print(f"  {case['label']:<28} {discount:>9.0f}%")


# ---------------------------------------------------------------------------
# DECORATOR (caché)
# ---------------------------------------------------------------------------


async def demo_decorator() -> None:
    print("\n" + "=" * 60)
    print("4. DECORATOR — CachedCatalogClient con caché en memoria")
    print("=" * 60)

    # Mock del cliente real
    mock_client = AsyncMock()
    call_count = 0

    async def fake_get(name: str) -> CatalogProductOut:
        nonlocal call_count
        call_count += 1
        return CatalogProductOut(
            product_id=f"SKU-{call_count:03d}",
            product_name=name,
            unit_price=Decimal("99.99"),
            currency="USD",
            available=True,
        )

    mock_client.get_product.side_effect = fake_get
    cached = CachedCatalogClient(client=mock_client, ttl=300)

    productos = [
        "Laptop Dell XPS 15",
        "Mouse Logitech MX Master",
        "Laptop Dell XPS 15",  # hit
        "Teclado mecánico",
        "Mouse Logitech MX Master",  # hit
        "Laptop Dell XPS 15",  # hit
    ]

    print(f"\n  Consultando {len(productos)} productos ({len(set(productos))} únicos)...\n")

    for nombre in productos:
        product = await cached.get_product(nombre)
        en_cache = "CACHE HIT " if nombre in productos[: productos.index(nombre)] else "CACHE MISS"
        print(f"  {en_cache} → {product.product_name}")

    stats = cached.stats
    print("\n  Estadísticas del caché:")
    print(f"    Hits           : {stats['hits']}")
    print(f"    Misses         : {stats['misses']}")
    print(f"    Hit rate       : {stats['hit_rate']:.1%}")
    print(f"    Productos en caché : {stats['cache_size']}")
    print(f"    Llamadas reales al cliente HTTP : {call_count}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 60)
    print("MÓDULO 13: PATRONES DE DISEÑO")
    print("Strategy · Builder · Adapter · Decorator")
    print("=" * 60)

    demo_strategy()
    demo_builder()
    demo_adapter()
    asyncio.run(demo_decorator())

    print("\n" + "=" * 60)
    print("✓ DEMO MÓDULO 13 COMPLETADO")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
