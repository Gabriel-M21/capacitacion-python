"""
Generadores para procesamiento eficiente de órdenes - Módulo 3
Demuestra: generadores, yield, iteradores, comprensiones
"""

import logging
from collections.abc import Generator
from typing import Any

logger = logging.getLogger(__name__)


def batch_processor(
    orders: list[dict[str, Any]], batch_size: int = 10
) -> Generator[list[dict[str, Any]], None, None]:
    """
    Generador que procesa órdenes en lotes.

    Args:
        orders: Lista de órdenes a procesar
        batch_size: Tamaño de cada lote

    Yields:
        Lotes de órdenes

    Example:
        for batch in batch_processor(all_orders, batch_size=50):
            process_batch(batch)
    """
    if batch_size <= 0:
        raise ValueError("batch_size debe ser mayor a 0")

    total_orders = len(orders)
    logger.info(f"Procesando {total_orders} órdenes en lotes de {batch_size}")

    for i in range(0, total_orders, batch_size):
        batch = orders[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_orders + batch_size - 1) // batch_size

        logger.debug(f"Generando lote {batch_num}/{total_batches} ({len(batch)} órdenes)")
        yield batch


def order_items_generator(
    orders: list[dict[str, Any]],
) -> Generator[tuple[str, dict[str, Any]], None, None]:
    """
    Generador que itera sobre todos los items de todas las órdenes.

    Args:
        orders: Lista de órdenes

    Yields:
        Tupla (order_id, item)

    Example:
        for order_id, item in order_items_generator(orders):
            print(f"Order {order_id}: {item['product_name']}")
    """
    for order in orders:
        order_id = order.get("order_id", "UNKNOWN")
        items = order.get("items", [])

        for item in items:
            yield order_id, item


def filter_orders_stream(
    orders: list[dict[str, Any]], predicate: Any
) -> Generator[dict[str, Any], None, None]:
    """
    Generador que filtra órdenes según un predicado (eficiente en memoria).

    Args:
        orders: Lista de órdenes
        predicate: Función que retorna True/False

    Yields:
        Órdenes que cumplen el predicado

    Example:
        high_value = filter_orders_stream(
            orders,
            lambda o: o.get('total', 0) > 100
        )
        for order in high_value:
            process_order(order)
    """
    for order in orders:
        if predicate(order):
            yield order


def transform_orders_stream(
    orders: list[dict[str, Any]], transformer: Any
) -> Generator[dict[str, Any], None, None]:
    """
    Generador que transforma órdenes sobre la marcha.

    Args:
        orders: Lista de órdenes
        transformer: Función que transforma cada orden

    Yields:
        Órdenes transformadas

    Example:
        enriched = transform_orders_stream(
            orders,
            lambda o: {**o, 'processed_at': datetime.now()}
        )
    """
    for order in orders:
        yield transformer(order)


def paginate_orders(
    orders: list[dict[str, Any]], page_size: int = 20
) -> Generator[tuple[int, list[dict[str, Any]]], None, None]:
    """
    Generador que pagina órdenes (útil para APIs).

    Args:
        orders: Lista de órdenes
        page_size: Tamaño de página

    Yields:
        Tupla (número_página, órdenes_de_página)

    Example:
        for page_num, page_orders in paginate_orders(all_orders, page_size=25):
            send_to_api(page_num, page_orders)
    """
    if page_size <= 0:
        raise ValueError("page_size debe ser mayor a 0")

    page_num = 1
    for i in range(0, len(orders), page_size):
        page_orders = orders[i : i + page_size]
        yield page_num, page_orders
        page_num += 1


class OrderIterator:
    """
    Iterador personalizado para órdenes con filtrado.
    Demuestra el protocolo de iterador (__iter__ y __next__).
    """

    def __init__(self, orders: list[dict[str, Any]], status_filter: str | None = None) -> None:
        """
        Inicializa el iterador.

        Args:
            orders: Lista de órdenes
            status_filter: Filtrar por status (opcional)
        """
        self.orders = orders
        self.status_filter = status_filter
        self.index = 0

    def __iter__(self) -> "OrderIterator":
        """Retorna el iterador mismo."""
        return self

    def __next__(self) -> dict[str, Any]:
        """
        Retorna la siguiente orden que cumple el filtro.

        Returns:
            Siguiente orden

        Raises:
            StopIteration: Cuando no hay más items
        """
        while self.index < len(self.orders):
            order = self.orders[self.index]
            self.index += 1

            # Si no hay filtro, retornar la orden
            if self.status_filter is None:
                return order

            # Si hay filtro, verificar status
            if order.get("status") == self.status_filter:
                return order

        raise StopIteration


# Comprensiones útiles para órdenes
def get_order_summaries(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Genera resúmenes usando comprensiones pythonic.

    Args:
        orders: Lista de órdenes

    Returns:
        Diccionario con varios resúmenes

    Example:
        summaries = get_order_summaries(orders)
        print(summaries['order_ids'])
    """
    # List comprehension: IDs de órdenes
    order_ids = [order["order_id"] for order in orders]

    # List comprehension con filtro: órdenes de alto valor
    high_value_orders = [order for order in orders if order.get("total", 0) > 100]

    # Dict comprehension: mapeo order_id -> total
    order_totals = {order["order_id"]: order.get("total", 0) for order in orders}

    # Set comprehension: clientes únicos
    unique_customers = {order.get("customer_name") for order in orders if "customer_name" in order}

    # Generator expression: suma de totales (eficiente)
    total_revenue = sum(order.get("total", 0) for order in orders)

    # Nested comprehension: todos los productos de todas las órdenes
    all_products = [
        item["product_name"]
        for order in orders
        for item in order.get("items", [])
        if "product_name" in item
    ]

    return {
        "order_ids": order_ids,
        "high_value_count": len(high_value_orders),
        "order_totals": order_totals,
        "unique_customers": unique_customers,
        "total_revenue": total_revenue,
        "all_products": all_products,
    }
