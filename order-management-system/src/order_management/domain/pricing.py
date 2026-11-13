"""
Pricing - Módulo 10: TDD
Reglas de descuento por volumen de items.
"""

from decimal import Decimal


def volume_discount(item_count: int) -> Decimal:
    """
    Calcula el porcentaje de descuento según cantidad de items.

    Args:
        item_count: Número de items en la orden

    Returns:
        Porcentaje de descuento como Decimal (0, 5, 10 o 15)

    Raises:
        ValueError: Si item_count es menor a 1
    """
    if item_count < 1:
        raise ValueError(f"item_count debe ser mayor a 0: {item_count}")

    if item_count <= 2:
        return Decimal("0")
    elif item_count <= 5:
        return Decimal("5")
    elif item_count <= 9:
        return Decimal("10")
    else:
        return Decimal("15")
