"""
Pruebas de patrones de diseño - Módulo 13
Verifica: Strategy, Builder, Adapter y Decorator con pytest.
"""

import asyncio
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from order_management.clients.cached_catalog_client import CachedCatalogClient
from order_management.domain.strategies import (
    MaxDiscountStrategy,
    NoDiscountStrategy,
    PricingStrategy,
    SeasonalDiscountStrategy,
    VIPDiscountStrategy,
    VolumeDiscountStrategy,
)
from order_management.domain.value_objects import OrderId, OrderStatus
from order_management.infrastructure.adapters.pricing_adapter import (
    ExternalPricingAdapter,
    ExternalPricingAPI,
)
from order_management.schemas.schemas import CatalogProductOut
from order_management.services.order_builder import OrderBuilder, OrderBuildError

# ---------------------------------------------------------------------------
# Fixtures compartidos
# ---------------------------------------------------------------------------


@pytest.fixture
def order_1_item() -> dict[str, Any]:
    return {
        "order_id": "ORD-001",
        "email": "juan.perez@example.com",
        "items": [{"product_name": "Laptop", "quantity": 1, "price": 1299.99}],
    }


@pytest.fixture
def order_6_items() -> dict[str, Any]:
    return {
        "order_id": "ORD-002",
        "email": "maria.garcia@example.com",
        "items": [
            {"product_name": f"Producto {i}", "quantity": 1, "price": 50.0} for i in range(6)
        ],
    }


@pytest.fixture
def order_gold_customer() -> dict[str, Any]:
    return {
        "order_id": "ORD-003",
        "email": "laura.gomez@example.com",
        "items": [{"product_name": "MacBook", "quantity": 1, "price": 1299.99}],
    }


# ---------------------------------------------------------------------------
# STRATEGY — PricingStrategy Protocol
# ---------------------------------------------------------------------------


def test_strategy_protocol_es_runtime_checkable():
    """PricingStrategy es verificable en runtime con isinstance."""
    assert isinstance(NoDiscountStrategy(), PricingStrategy)
    assert isinstance(VolumeDiscountStrategy(), PricingStrategy)
    assert isinstance(SeasonalDiscountStrategy(), PricingStrategy)


def test_no_discount_strategy_devuelve_cero(order_1_item):
    strategy = NoDiscountStrategy()
    assert strategy.calculate_discount(order_1_item) == Decimal("0")


@pytest.mark.parametrize(
    "quantities, expected",
    [
        ([1], Decimal("0")),  # 1 item → 0%
        ([1, 1], Decimal("0")),  # 2 items → 0%
        ([1, 1, 1], Decimal("5")),  # 3 items → 5%
        ([2, 2, 2], Decimal("10")),  # 6 qty en 3 productos → 10%
        ([1] * 6, Decimal("10")),  # 6 items → 10%
        ([1] * 10, Decimal("15")),  # 10 items → 15%
    ],
)
def test_volume_discount_strategy_tramos(quantities: list, expected: Decimal):
    strategy = VolumeDiscountStrategy()
    order = {
        "items": [
            {"product_name": f"P{i}", "quantity": q, "price": 10.0}
            for i, q in enumerate(quantities)
        ]
    }
    assert strategy.calculate_discount(order) == expected


def test_seasonal_discount_strategy_aplica_fijo(order_1_item):
    strategy = SeasonalDiscountStrategy(discount_percentage=Decimal("15"))
    assert strategy.calculate_discount(order_1_item) == Decimal("15")


def test_seasonal_discount_strategy_invalido():
    with pytest.raises(ValueError):
        SeasonalDiscountStrategy(discount_percentage=Decimal("150"))


def test_vip_discount_strategy_cliente_vip(order_gold_customer):
    strategy = VIPDiscountStrategy(
        vip_emails={"laura.gomez@example.com"},
        vip_discount=Decimal("20"),
    )
    assert strategy.calculate_discount(order_gold_customer) == Decimal("20")


def test_vip_discount_strategy_cliente_no_vip(order_1_item):
    strategy = VIPDiscountStrategy(
        vip_emails={"otro@example.com"},
        vip_discount=Decimal("20"),
    )
    # Fallback a VolumeDiscountStrategy → 1 item → 0%
    assert strategy.calculate_discount(order_1_item) == Decimal("0")


def test_max_discount_strategy_elige_maximo(order_6_items):
    strategies: list[PricingStrategy] = [
        NoDiscountStrategy(),  # → 0%
        SeasonalDiscountStrategy(Decimal("8")),  # → 8%
        VolumeDiscountStrategy(),  # → 10% (6 items)
    ]
    strategy = MaxDiscountStrategy(strategies=strategies)
    assert strategy.calculate_discount(order_6_items) == Decimal("10")


def test_max_discount_strategy_vacia_lanza_error():
    with pytest.raises(ValueError):
        MaxDiscountStrategy(strategies=[])


# ---------------------------------------------------------------------------
# BUILDER — OrderBuilder
# ---------------------------------------------------------------------------


def test_builder_construye_orden_completa():
    order = (
        OrderBuilder(order_id=OrderId.generate(1))
        .with_customer("Juan Pérez", "juan.perez@example.com", "+52 55 1234")
        .add_item("Laptop Dell XPS 15", quantity=1, unit_price=1299.99)
        .add_item("Mouse Logitech", quantity=2, unit_price=29.99)
        .with_notes("Entrega urgente")
        .build()
    )

    assert str(order.order_id) == "ORD-00001"
    assert order.customer.name == "Juan Pérez"
    assert len(order.items) == 2
    assert order.notes == "Entrega urgente"
    assert order.status == OrderStatus.PENDING


def test_builder_sin_cliente_lanza_error():
    builder = OrderBuilder(order_id=OrderId.generate(1)).add_item(
        "Laptop", quantity=1, unit_price=999.0
    )
    with pytest.raises(OrderBuildError, match="cliente"):
        builder.build()


def test_builder_sin_items_lanza_error():
    builder = OrderBuilder(order_id=OrderId.generate(1)).with_customer("Juan", "juan@example.com")
    with pytest.raises(OrderBuildError, match="item"):
        builder.build()


def test_builder_calcula_total_correcto():
    order = (
        OrderBuilder(order_id=OrderId.generate(1))
        .with_customer("Test", "test@example.com")
        .add_item("Producto A", quantity=2, unit_price=100.0)
        .add_item("Producto B", quantity=1, unit_price=50.0)
        .build()
    )
    from order_management.domain.value_objects import Money

    expected = Money.from_float(250.0)
    assert order.total == expected


def test_builder_express_order_factory_method():
    order = (
        OrderBuilder.express_order(
            order_id=OrderId.generate(99),
            customer_name="Cliente VIP",
            customer_email="vip@example.com",
        )
        .add_item("Producto Premium", quantity=1, unit_price=500.0)
        .build()
    )

    assert order.status == OrderStatus.CONFIRMED
    assert order.notes is not None
    assert "express" in order.notes.lower()


def test_builder_es_reutilizable():
    """El Builder puede construir múltiples órdenes distintas."""
    base = (
        OrderBuilder(order_id=OrderId.generate(1))
        .with_customer("Juan", "juan@example.com")
        .add_item("Base", quantity=1, unit_price=100.0)
    )

    order_a = base.with_notes("Nota A").build()
    order_b = (
        OrderBuilder(order_id=OrderId.generate(2))
        .with_customer("María", "maria@example.com")
        .add_item("Otro", quantity=1, unit_price=200.0)
        .build()
    )

    assert order_a.customer.name == "Juan"
    assert order_b.customer.name == "María"


# ---------------------------------------------------------------------------
# ADAPTER — ExternalPricingAdapter
# ---------------------------------------------------------------------------


def test_adapter_cumple_pricing_strategy_protocol():
    adapter = ExternalPricingAdapter()
    assert isinstance(adapter, PricingStrategy)


def test_adapter_cliente_gold_descuento_20(order_gold_customer):
    adapter = ExternalPricingAdapter()
    discount = adapter.calculate_discount(order_gold_customer)
    assert discount == Decimal("20")


def test_adapter_cliente_silver_con_items(order_6_items):
    adapter = ExternalPricingAdapter()
    discount = adapter.calculate_discount(order_6_items)
    assert discount == Decimal("10")


def test_adapter_cliente_sin_tier_sin_descuento(order_1_item):
    """Cliente sin tier y total < 1000 → 0% de descuento."""
    order = {
        "email": "desconocido@noexiste.com",
        "items": [{"product_name": "Barato", "quantity": 1, "price": 10.0}],
    }
    adapter = ExternalPricingAdapter()
    assert adapter.calculate_discount(order) == Decimal("0")


def test_adapter_usa_api_externa_inyectada():
    """El Adapter acepta una API inyectada — testeable sin red."""
    mock_api = ExternalPricingAPI()
    adapter = ExternalPricingAdapter(api=mock_api)
    order = {
        "email": "admin@example.com",
        "items": [{"product_name": "Laptop", "quantity": 1, "price": 600.0}],
    }
    discount = adapter.calculate_discount(order)
    assert discount == Decimal("20")  # GOLD + total > 500


# ---------------------------------------------------------------------------
# DECORATOR — CachedCatalogClient
# ---------------------------------------------------------------------------


def _make_cached_client() -> tuple[CachedCatalogClient, AsyncMock]:
    """Crea un CachedCatalogClient con un cliente mock subyacente."""
    mock_client = AsyncMock()
    mock_client.get_product.return_value = CatalogProductOut(
        product_id="SKU-001",
        product_name="Laptop Dell XPS 15",
        unit_price=Decimal("1299.99"),
        currency="USD",
        available=True,
    )
    cached = CachedCatalogClient(client=mock_client, ttl=60)
    return cached, mock_client


def test_decorator_primera_llamada_va_al_cliente_real():
    cached, mock_client = _make_cached_client()

    async def run():
        await cached.get_product("Laptop Dell XPS 15")

    asyncio.run(run())
    mock_client.get_product.assert_called_once_with("Laptop Dell XPS 15")


def test_decorator_segunda_llamada_usa_cache():
    cached, mock_client = _make_cached_client()

    async def run():
        await cached.get_product("Laptop Dell XPS 15")
        await cached.get_product("Laptop Dell XPS 15")

    asyncio.run(run())
    # El cliente real solo se llamó una vez
    assert mock_client.get_product.call_count == 1
    assert cached.stats["hits"] == 1
    assert cached.stats["misses"] == 1


def test_decorator_productos_distintos_consultan_cliente():
    mock_client = AsyncMock()

    async def make_product(name: str) -> CatalogProductOut:
        return CatalogProductOut(
            product_id="SKU-X",
            product_name=name,
            unit_price=Decimal("99.99"),
            currency="USD",
            available=True,
        )

    mock_client.get_product.side_effect = make_product
    cached = CachedCatalogClient(client=mock_client)

    async def run() -> None:
        await cached.get_product("Producto A")
        await cached.get_product("Producto B")
        await cached.get_product("Producto A")  # hit

    asyncio.run(run())
    assert mock_client.get_product.call_count == 2
    assert cached.stats["hits"] == 1
    assert cached.cache_size == 2


def test_decorator_hit_rate():
    cached, _ = _make_cached_client()

    async def run():
        for _ in range(3):
            await cached.get_product("Laptop Dell XPS 15")

    asyncio.run(run())
    # 1 miss + 2 hits → hit_rate = 2/3
    assert cached.hit_rate == pytest.approx(2 / 3, rel=1e-2)


def test_decorator_invalidate_limpia_cache():
    cached, mock_client = _make_cached_client()

    async def run():
        await cached.get_product("Laptop Dell XPS 15")
        cached.invalidate("Laptop Dell XPS 15")
        await cached.get_product("Laptop Dell XPS 15")

    asyncio.run(run())
    # Después de invalidar, consulta de nuevo al cliente real
    assert mock_client.get_product.call_count == 2


def test_decorator_invalidate_all():
    cached, mock_client = _make_cached_client()

    async def run():
        await cached.get_product("Laptop Dell XPS 15")
        cached.invalidate()  # vacía todo
        assert cached.cache_size == 0

    asyncio.run(run())
