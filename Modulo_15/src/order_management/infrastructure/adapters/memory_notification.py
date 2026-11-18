"""
Adaptador de notificación en memoria - Módulo 15: Arquitectura Hexagonal

Implementación de NotificationPort que almacena notificaciones en memoria.
Útil para:
  - Tests unitarios y de contrato (sin red ni infraestructura)
  - Demos y desarrollo local
  - Verificar LSP: intercambiable con HttpNotificationAdapter
"""

from typing import Any

from order_management.domain.ports import NotificationPort


class InMemoryNotificationAdapter:
    """
    Implementación de NotificationPort que guarda notificaciones en memoria.

    LSP: completamente intercambiable con HttpNotificationAdapter
         desde el punto de vista de CreateOrderUseCase.

    Example:
        notifier = InMemoryNotificationAdapter()
        use_case = CreateOrderUseCase(repo, notifier)
        use_case.execute(command)

        # En tests, verificar que se envió la notificación:
        assert notifier.was_notified("ORD-00001")
        assert notifier.last_notification["customer_email"] == "juan@example.com"
    """

    def __init__(self) -> None:
        self._notifications: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # NotificationPort
    # ------------------------------------------------------------------

    def order_created(
        self,
        order_id: str,
        customer_email: str,
        total: float,
    ) -> None:
        """Registra la notificación de orden creada en memoria."""
        self._notifications.append(
            {
                "event": "order_created",
                "order_id": order_id,
                "customer_email": customer_email,
                "total": total,
            }
        )

    def order_status_changed(
        self,
        order_id: str,
        old_status: str,
        new_status: str,
    ) -> None:
        """Registra la notificación de cambio de estado en memoria."""
        self._notifications.append(
            {
                "event": "order_status_changed",
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
            }
        )

    # ------------------------------------------------------------------
    # Helpers para tests
    # ------------------------------------------------------------------

    @property
    def all_notifications(self) -> list[dict[str, Any]]:
        """Lista de todas las notificaciones enviadas."""
        return list(self._notifications)

    @property
    def last_notification(self) -> dict[str, Any] | None:
        """Última notificación enviada."""
        return self._notifications[-1] if self._notifications else None

    @property
    def notification_count(self) -> int:
        """Número total de notificaciones enviadas."""
        return len(self._notifications)

    def was_notified(self, order_id: str) -> bool:
        """Verifica si se envió alguna notificación para esta orden."""
        return any(n["order_id"] == order_id for n in self._notifications)

    def notifications_for(self, order_id: str) -> list[dict[str, Any]]:
        """Devuelve todas las notificaciones de una orden específica."""
        return [n for n in self._notifications if n["order_id"] == order_id]

    def clear(self) -> None:
        """Vacía el historial de notificaciones."""
        self._notifications.clear()


# Verificación estática: cumple NotificationPort
def _assert_protocol_compliance() -> None:
    _: NotificationPort = InMemoryNotificationAdapter()
