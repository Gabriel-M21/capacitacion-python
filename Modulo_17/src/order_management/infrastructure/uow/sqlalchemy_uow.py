"""
Unit of Work SQLAlchemy - Módulo 16: Arquitectura Limpia

Implementación de UnitOfWorkPort que usa SQLAlchemy para garantizar
atomicidad real con transacciones de base de datos.

LSP: completamente intercambiable con InMemoryUnitOfWork desde el
     punto de vista de CreateOrderUseCase.
"""

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from order_management.domain.events import DomainEvent
from order_management.infrastructure.db.repositories.order_repository import OrderRepository


class SqlAlchemyUnitOfWork:
    """
    Implementación de UoW con SQLAlchemy.

    - Envuelve una sesión SQLAlchemy en una transacción
    - Hace commit o rollback automático según el resultado
    - Acumula eventos de dominio para publicar después del commit

    Example:
        engine = create_engine("sqlite:///orders.db")
        Session = sessionmaker(bind=engine)
        uow = SqlAlchemyUnitOfWork(Session)

        with uow:
            uow.orders.save(order)
            uow.add_event(OrderCreated(...))
            uow.commit()

        bus.publish_all(uow.collect_events())
    """

    def __init__(self, session_factory: sessionmaker) -> None:  # type: ignore[type-arg]
        self._session_factory = session_factory
        self._session: Session | None = None
        self._events: list[DomainEvent] = []
        self.orders: OrderRepository | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.orders = OrderRepository(self._session)
        self._events.clear()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rollback()
        if self._session:
            self._session.close()

    # ------------------------------------------------------------------
    # UnitOfWorkPort
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """Persiste todos los cambios en la base de datos."""
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Descarta todos los cambios de la transacción actual."""
        if self._session:
            self._session.rollback()

    def collect_events(self) -> list[DomainEvent]:
        """Devuelve y vacía los eventos pendientes de publicar."""
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def add_event(self, event: DomainEvent) -> None:
        """Acumula un evento para publicar después del commit."""
        self._events.append(event)
