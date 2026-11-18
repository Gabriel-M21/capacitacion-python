"""
Repositorio en memoria - Módulo 12: SOLID / Módulo 15: Arquitectura Hexagonal
Implementación de OrderRepositoryPort para tests y demos.

LSP: es completamente intercambiable con JsonFileOrderRepository
     desde el punto de vista de OrderService, y con OrderRepository
     (SQLAlchemy) desde el punto de vista de CreateOrderUseCase.
OCP: nueva implementación sin tocar nada existente.
"""

from typing import Any

from order_management.domain.entities import Order
from order_management.domain.ports import OrderRepositoryPort


class InMemoryOrderRepository:
    """
    Implementación de OrderRepositoryPort que opera en memoria.

    Útil para:
      - Tests unitarios rápidos (sin E/S)
      - Demos y prototipos
      - Verificación de LSP: OrderService y CreateOrderUseCase
        funcionan igual con esta implementación.
    """

    def __init__(self, orders: list[Any] | None = None) -> None:
        self._orders: list[Any] = orders or []
        self.saved_summaries: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # OrderRepositoryPort — para OrderService (Módulo 12)
    # ------------------------------------------------------------------

    def load_orders(self) -> list[dict[str, Any]]:
        """Devuelve las órdenes cargadas en memoria como dicts."""
        return [o for o in self._orders if isinstance(o, dict)]

    def save_summary(self, summary: dict[str, Any]) -> None:
        """Guarda el resumen en memoria (accesible en tests)."""
        self.saved_summaries.append(summary)

    # ------------------------------------------------------------------
    # Métodos de dominio — para CreateOrderUseCase (Módulo 15)
    # ------------------------------------------------------------------

    def save(self, order: Order) -> None:
        """Guarda o actualiza una Order de dominio en memoria."""
        self._orders = [
            o
            for o in self._orders
            if not isinstance(o, Order) or str(o.order_id) != str(order.order_id)
        ]
        self._orders.append(order)

    def get_by_order_id(self, order_id: str) -> Order | None:
        """Busca una Order por su order_id."""
        return next(
            (o for o in self._orders if isinstance(o, Order) and str(o.order_id) == order_id),
            None,
        )

    def list_all(self) -> list[Order]:
        """Devuelve todas las órdenes de dominio en memoria."""
        return [o for o in self._orders if isinstance(o, Order)]

    # ------------------------------------------------------------------
    # Helpers para tests
    # ------------------------------------------------------------------

    def add_order(self, order: dict[str, Any]) -> None:
        """Añade una orden como dict al repositorio."""
        self._orders.append(order)

    def clear(self) -> None:
        """Vacía órdenes y resúmenes guardados."""
        self._orders.clear()
        self.saved_summaries.clear()

    @property
    def last_summary(self) -> dict[str, Any] | None:
        """Último resumen guardado (útil en assertions de tests)."""
        return self.saved_summaries[-1] if self.saved_summaries else None


# Verificación estática: InMemoryOrderRepository cumple el Protocol
def _assert_protocol_compliance() -> None:
    _: OrderRepositoryPort = InMemoryOrderRepository()
