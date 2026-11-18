"""
Puertos del dominio - Módulo 15: Arquitectura Hexagonal
Define los contratos (Protocols) que el dominio espera de la infraestructura.

DIP: el dominio depende de abstracciones, no de implementaciones concretas.
ISP: cada Protocol tiene una responsabilidad mínima y coherente.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OrderRepositoryPort(Protocol):
    """
    Puerto de lectura/escritura de órdenes.

    Cualquier clase que implemente estos métodos cumple el contrato,
    sin necesidad de herencia explícita (duck typing estructural).

    Implementaciones actuales:
      - JsonFileOrderRepository   (producción / Módulo 6)
      - InMemoryOrderRepository   (tests / demos)
      - OrderRepository           (SQLAlchemy / Módulo 8)
    """

    def load_orders(self) -> list[dict[str, Any]]:
        """
        Carga y devuelve todas las órdenes disponibles.

        Returns:
            Lista de órdenes como diccionarios
        """
        ...

    def save_summary(self, summary: dict[str, Any]) -> None:
        """
        Persiste el resumen/estadísticas generadas por OrderService.

        Args:
            summary: Diccionario con estadísticas a guardar
        """
        ...


@runtime_checkable
class OrderValidatorPort(Protocol):
    """
    Puerto de validación de órdenes.

    ISP: separado de OrderRepositoryPort porque validar y persistir
    son responsabilidades distintas.
    """

    def validate(self, order: dict[str, Any]) -> tuple[bool, str]:
        """
        Valida una orden individual.

        Args:
            order: Diccionario con datos de la orden

        Returns:
            Tupla (es_válida, mensaje_error)
        """
        ...


@runtime_checkable
class NotificationPort(Protocol):
    """
    Puerto de notificaciones — Módulo 15: Arquitectura Hexagonal.

    El dominio y los casos de uso dependen de este Protocol,
    nunca de implementaciones concretas (HTTP, email, SMS, etc.).

    Implementaciones:
      - InMemoryNotificationAdapter  (tests y demos)
      - HttpNotificationAdapter      (producción con Smocker)
    """

    def order_created(self, order_id: str, customer_email: str, total: float) -> None:
        """
        Notifica que una orden fue creada exitosamente.

        Args:
            order_id:       ID de la orden creada (ej. 'ORD-00001')
            customer_email: Email del cliente para la notificación
            total:          Total de la orden en la moneda base
        """
        ...

    def order_status_changed(
        self,
        order_id: str,
        old_status: str,
        new_status: str,
    ) -> None:
        """
        Notifica que el estado de una orden cambió.

        Args:
            order_id:   ID de la orden
            old_status: Estado anterior
            new_status: Nuevo estado
        """
        ...
