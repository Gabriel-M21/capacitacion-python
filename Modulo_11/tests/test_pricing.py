"""
Pruebas de pricing con TDD - Módulo 10
Cubre: fixtures, parametrización, markers, mocking, Hypothesis y cobertura.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from order_management.domain.pricing import volume_discount
from order_management.domain.value_objects import Money

# ---------------------------------------------------------------------------
# CICLO 2-6: Parametrización — todos los tramos de descuento
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "item_count, expected_discount",
    [
        (1, Decimal("0")),  # límite inferior tramo 0%
        (2, Decimal("0")),  # límite superior tramo 0%
        (3, Decimal("5")),  # límite inferior tramo 5%
        (5, Decimal("5")),  # límite superior tramo 5%
        (6, Decimal("10")),  # límite inferior tramo 10%
        (9, Decimal("10")),  # límite superior tramo 10%
        (10, Decimal("15")),  # límite inferior tramo 15%
        (100, Decimal("15")),  # valor alto → siempre 15%
    ],
)
def test_volume_discount_tramos(item_count: int, expected_discount: Decimal) -> None:
    """Verifica todos los tramos de descuento con parametrización."""
    assert volume_discount(item_count) == expected_discount


# ---------------------------------------------------------------------------
# CICLO 7: Validación — entrada inválida
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", [0, -1, -100])
def test_volume_discount_invalido_lanza_error(bad_value: int) -> None:
    """item_count <= 0 debe lanzar ValueError."""
    with pytest.raises(ValueError, match="item_count debe ser mayor a 0"):
        volume_discount(bad_value)


# ---------------------------------------------------------------------------
# CICLO 8: Mocking — aislar la función de dependencias externas
# ---------------------------------------------------------------------------


def test_volume_discount_con_mock_de_orden() -> None:
    """
    Demuestra mocking: simula que una orden tiene 6 items
    sin construir objetos reales de dominio.
    """
    with patch(
        "order_management.domain.pricing.volume_discount",
        return_value=Decimal("10"),
    ) as mock_fn:
        result = mock_fn(6)
        mock_fn.assert_called_once_with(6)
        assert result == Decimal("10")


# ---------------------------------------------------------------------------
# CICLO 9: Property-based testing con Hypothesis
# ---------------------------------------------------------------------------


@given(st.integers(min_value=1, max_value=10_000))
@settings(max_examples=500)
def test_descuento_siempre_entre_0_y_15(item_count: int) -> None:
    """
    Propiedad: para cualquier item_count >= 1,
    el descuento siempre está en {0, 5, 10, 15}.
    """
    result = volume_discount(item_count)
    assert result in {Decimal("0"), Decimal("5"), Decimal("10"), Decimal("15")}


@given(st.integers(min_value=1, max_value=10_000))
def test_descuento_es_monotono(item_count: int) -> None:
    """
    Propiedad: más items nunca bajan el descuento.
    volume_discount(n+1) >= volume_discount(n)
    """
    if item_count < 10_000:
        assert volume_discount(item_count + 1) >= volume_discount(item_count)


@given(st.integers(min_value=1, max_value=2))
def test_tramo_cero_por_ciento(item_count: int) -> None:
    """Propiedad: 1-2 items siempre dan 0%."""
    assert volume_discount(item_count) == Decimal("0")


@given(st.integers(min_value=3, max_value=5))
def test_tramo_cinco_por_ciento(item_count: int) -> None:
    """Propiedad: 3-5 items siempre dan 5%."""
    assert volume_discount(item_count) == Decimal("5")


@given(st.integers(min_value=6, max_value=9))
def test_tramo_diez_por_ciento(item_count: int) -> None:
    """Propiedad: 6-9 items siempre dan 10%."""
    assert volume_discount(item_count) == Decimal("10")


@given(st.integers(min_value=10, max_value=10_000))
def test_tramo_quince_por_ciento(item_count: int) -> None:
    """Propiedad: 10+ items siempre dan 15%."""
    assert volume_discount(item_count) == Decimal("15")


# ---------------------------------------------------------------------------
# CICLO 10: Integración con Money del dominio
# ---------------------------------------------------------------------------


@pytest.fixture
def precio_base() -> Money:
    """Fixture: precio base de un producto."""
    return Money.from_float(100.00)


def test_descuento_aplicado_a_money(precio_base: Money) -> None:
    """
    Integra volume_discount con Money:
    verifica que el descuento reduce el precio correctamente.
    """
    item_count = 6  # → 10% descuento
    descuento = volume_discount(item_count)
    factor = (Decimal("100") - descuento) / Decimal("100")
    precio_final = precio_base * factor

    assert precio_final == Money.from_float(90.00)


@pytest.mark.parametrize(
    "item_count, precio, esperado",
    [
        (1, 100.0, 100.00),  # 0% → sin descuento
        (3, 100.0, 95.00),  # 5%
        (6, 100.0, 90.00),  # 10%
        (10, 100.0, 85.00),  # 15%
    ],
)
def test_precio_final_con_descuento(item_count: int, precio: float, esperado: float) -> None:
    """Precio final correcto para cada tramo de descuento."""
    base = Money.from_float(precio)
    factor = (Decimal("100") - volume_discount(item_count)) / Decimal("100")
    resultado = base * factor
    assert resultado == Money.from_float(esperado)
