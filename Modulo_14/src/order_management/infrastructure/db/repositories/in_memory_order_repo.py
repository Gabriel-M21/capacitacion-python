"""
Repositorio en memoria - Módulo 12: SOLID
Implementación de OrderRepositoryPort para tests y demos.

LSP: es completamente intercambiable con JsonFileOrderRepository
     desde el punto de vista de OrderService.
OCP: nueva implementación sin tocar nada existente.
"""

from typing import Any

from order_management.domain.ports import OrderRepositoryPort


class InMemoryOrderRepository:
    """
    Implementación de OrderRepositoryPort que opera en memoria.

    Útil para:
      - Tests unitarios rápidos (sin E/S)
      - Demos y prototipos
      - Verificación de LSP: OrderService funciona igual con esta
        implementación que con JsonFileOrderRepository.
    """

    def __init__(self, orders: list[dict[str, Any]] | None = None) -> None:
        self._orders: list[dict[str, Any]] = orders or []
        self.saved_summaries: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # OrderRepositoryPort
    # ------------------------------------------------------------------

    def load_orders(self) -> list[dict[str, Any]]:
        """Devuelve las órdenes cargadas en memoria."""
        return list(self._orders)

    def save_summary(self, summary: dict[str, Any]) -> None:
        """Guarda el resumen en memoria (accesible en tests)."""
        self.saved_summaries.append(summary)

    # ------------------------------------------------------------------
    # Helpers para tests
    # ------------------------------------------------------------------

    def add_order(self, order: dict[str, Any]) -> None:
        """Añade una orden al repositorio en memoria."""
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
