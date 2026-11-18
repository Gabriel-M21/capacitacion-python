"""
Bus de eventos - Módulo 16: Arquitectura Limpia

El EventBus desacopla al publicador (caso de uso) de los manejadores
(notificación, métricas, auditoría). El caso de uso solo publica
eventos; no sabe quién los maneja ni cuándo.

Patrón: Observer / Mediator aplicado a eventos de dominio.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from order_management.domain.events import DomainEvent

logger = logging.getLogger(__name__)

# Tipo de un manejador de eventos
EventHandler = Callable[[Any], None]


class EventBus:
    """
    Bus de eventos en memoria.

    Permite registrar múltiples handlers por tipo de evento y
    publicar eventos para que todos sus handlers los procesen.

    Example:
        bus = EventBus()

        @bus.subscribe(OrderCreated)
        def on_order_created(event: OrderCreated) -> None:
            send_email(event.customer_email)

        bus.publish(OrderCreated(order_id="ORD-001", ...))
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type,
    ) -> Callable[[EventHandler], EventHandler]:
        """
        Decorador para registrar un handler para un tipo de evento.

        Args:
            event_type: Clase del evento a manejar

        Returns:
            Decorador que registra la función como handler
        """

        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers[event_type].append(handler)
            logger.debug(
                "Handler '%s' registrado para '%s'",
                handler.__name__,
                event_type.__name__,
            )
            return handler

        return decorator

    def register(self, event_type: type, handler: EventHandler) -> None:
        """
        Registra un handler programáticamente (sin decorador).

        Args:
            event_type: Clase del evento
            handler:    Función que maneja el evento
        """
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        """
        Publica un evento a todos sus handlers registrados.

        Los errores en handlers individuales se loguean pero no
        interrumpen la publicación a los demás handlers.

        Args:
            event: Evento de dominio a publicar
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug("Evento '%s' publicado sin handlers", event_type.__name__)
            return

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    "Error en handler '%s' para evento '%s': %s",
                    handler.__name__,
                    event_type.__name__,
                    exc,
                )

    def publish_all(self, events: list[DomainEvent]) -> None:
        """
        Publica una lista de eventos en orden.

        Args:
            events: Lista de eventos a publicar
        """
        for event in events:
            self.publish(event)

    def handler_count(self, event_type: type) -> int:
        """Número de handlers registrados para un tipo de evento."""
        return len(self._handlers.get(event_type, []))

    def clear(self) -> None:
        """Elimina todos los handlers (útil en tests)."""
        self._handlers.clear()
