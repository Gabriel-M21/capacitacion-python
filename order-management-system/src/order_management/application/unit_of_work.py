"""
Unit of Work - Módulo 16: Arquitectura Limpia

El Unit of Work (UoW) garantiza que un conjunto de operaciones
se ejecute de forma atómica: o todas tienen éxito o ninguna persiste.

Resuelve el problema de tener múltiples repositorios en una misma
transacción: en vez de pasar session a cada repositorio, el UoW
los agrupa y controla el commit/rollback.

Uso:
    with uow:
        uow.orders.save(order)
        uow.commit()
    # Si algo falla → rollback automático en __exit__
"""

from typing import Any, Protocol, runtime_checkable

from order_management.domain.events import DomainEvent
from order_management.infrastructure.db.repositories.in_memory_order_repo import (
    InMemoryOrderRepository,
)


@runtime_checkable
class UnitOfWorkPort(Protocol):
    """
    Puerto del Unit of Work.

    Garantiza que el caso de uso trabaje con una única
    unidad de trabajo atómica sin conocer detalles de
    la implementación (SQL, memoria, etc.).
    """

    orders: Any  # OrderRepository compatible

    def __enter__(self) -> "UnitOfWorkPort":
        """Inicia la unidad de trabajo."""
        ...

    def __exit__(self, *args: Any) -> None:
        """Finaliza la unidad de trabajo con rollback si hay error."""
        ...

    def commit(self) -> None:
        """Persiste todos los cambios acumulados."""
        ...

    def rollback(self) -> None:
        """Descarta todos los cambios acumulados."""
        ...

    def collect_events(self) -> list[DomainEvent]:
        """Recoge los eventos de dominio pendientes de publicar."""
        ...


class InMemoryUnitOfWork:
    """
    Implementación de UoW en memoria para tests y demos.

    - No usa base de datos ni transacciones reales
    - Permite verificar que el caso de uso llama a commit()
    - Recoge eventos de dominio generados durante la operación
    """

    def __init__(self) -> None:
        self.orders = InMemoryOrderRepository()
        self._committed = False
        self._events: list[DomainEvent] = []

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "InMemoryUnitOfWork":
        self._committed = False
        self._events.clear()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()

    # ------------------------------------------------------------------
    # UnitOfWorkPort
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """Marca la operación como completada."""
        self._committed = True

    def rollback(self) -> None:
        """Descarta cambios (en memoria simplemente limpia el repo)."""
        self.orders.clear()
        self._committed = False

    def collect_events(self) -> list[DomainEvent]:
        """Devuelve y vacía los eventos pendientes."""
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Helpers para tests
    # ------------------------------------------------------------------

    def add_event(self, event: DomainEvent) -> None:
        """Añade un evento al buffer (llamado por el caso de uso)."""
        self._events.append(event)

    @property
    def was_committed(self) -> bool:
        """True si se llamó a commit() al menos una vez."""
        return self._committed
