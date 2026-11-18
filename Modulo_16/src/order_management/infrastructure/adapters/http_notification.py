"""
Adaptador de notificación HTTP - Módulo 15: Arquitectura Hexagonal

Implementación de NotificationPort que envía notificaciones via HTTP.
En el laboratorio apunta a Smocker; en producción apuntaría al
servicio real de notificaciones.

LSP: intercambiable con InMemoryNotificationAdapter sin cambiar
     CreateOrderUseCase ni ningún otro código.
"""

import json
import logging
from typing import Any

import httpx

from order_management.domain.ports import NotificationPort

logger = logging.getLogger(__name__)

# Ruta del endpoint de notificaciones en Smocker / servicio real
NOTIFY_PATH = "/notifications/orders"


class HttpNotificationAdapter:
    """
    Adaptador de NotificationPort que envía eventos via HTTP POST.

    En el laboratorio usa Smocker como destino simulado.
    En producción apuntaría a un servicio de notificaciones real
    (email, SMS, webhook, etc.).

    Example:
        notifier = HttpNotificationAdapter(
            base_url="http://localhost:8080",
            timeout=3.0,
        )
        use_case = CreateOrderUseCase(repo, notifier)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 3.0,
        raise_on_error: bool = False,
    ) -> None:
        """
        Args:
            base_url:       URL base del servicio de notificaciones
            timeout:        Timeout en segundos por petición
            raise_on_error: Si True, propaga excepciones HTTP.
                            Si False (default), solo loguea el error
                            para no interrumpir el flujo principal.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._raise = raise_on_error

    # ------------------------------------------------------------------
    # NotificationPort
    # ------------------------------------------------------------------

    def order_created(
        self,
        order_id: str,
        customer_email: str,
        total: float,
    ) -> None:
        """Envía evento order_created al servicio HTTP."""
        self._post(
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
        """Envía evento order_status_changed al servicio HTTP."""
        self._post(
            {
                "event": "order_status_changed",
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
            }
        )

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    def _post(self, payload: dict[str, Any]) -> None:
        """Realiza el POST HTTP con manejo de errores configurable."""
        url = self._base_url + NOTIFY_PATH
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
            if response.is_success:
                logger.info(
                    "Notificación enviada → %s [%d]",
                    payload.get("event"),
                    response.status_code,
                )
            else:
                logger.warning(
                    "Notificación respondió %d para evento '%s'",
                    response.status_code,
                    payload.get("event"),
                )
                if self._raise:
                    response.raise_for_status()

        except httpx.RequestError as exc:
            logger.warning(
                "Error de red al notificar '%s': %s",
                payload.get("event"),
                exc,
            )
            if self._raise:
                raise


# Verificación estática: cumple NotificationPort
def _assert_protocol_compliance() -> None:
    _: NotificationPort = HttpNotificationAdapter(base_url="http://localhost:8080")
