"""
Caso de uso CreateOrder - Módulo 15: Arquitectura Hexagonal

El caso de uso es el corazón de la capa de aplicación:
  - Orquesta dominio e infraestructura
  - Depende SOLO de puertos (Protocols), nunca de implementaciones concretas
  - No importa nada de SQLAlchemy, httpx, FastAPI ni archivos

Flujo:
  CreateOrderCommand
      ↓  validar
      ↓  construir Order (dominio)
      ↓  persistir (OrderRepositoryPort)
      ↓  notificar (NotificationPort)
      ↓
  OrderCreatedResult
"""

import logging

from order_management.application.dtos import (
    CreateOrderCommand,
    OrderCreatedResult,
    OrderItemResult,
)
from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.ports import NotificationPort, OrderRepositoryPort
from order_management.domain.value_objects import Email, Money, OrderId

logger = logging.getLogger(__name__)


class OrderAlreadyExistsError(Exception):
    """Se intenta crear una orden con un ID que ya existe."""


class CreateOrderUseCase:
    """
    Caso de uso: Crear una nueva orden de compra.

    DIP: depende de puertos (Protocols), no de implementaciones.
    SRP: su única razón de cambiar es la lógica de creación de órdenes.
    OCP: añadir un nuevo adaptador (notificación por SMS, email, etc.)
         no modifica este caso de uso.

    Example:
        repo     = SqlAlchemyOrderRepository(session)
        notifier = HttpNotificationAdapter(base_url="http://localhost:8080")
        use_case = CreateOrderUseCase(repository=repo, notifier=notifier)
        result   = use_case.execute(command)
    """

    def __init__(
        self,
        repository: OrderRepositoryPort,
        notifier: NotificationPort,
    ) -> None:
        """
        Args:
            repository: Adaptador de persistencia (SQL, memoria, etc.)
            notifier:   Adaptador de notificaciones (HTTP, email, memoria)
        """
        self._repo = repository
        self._notifier = notifier

    def execute(self, command: CreateOrderCommand) -> OrderCreatedResult:
        """
        Ejecuta el caso de uso CreateOrder.

        Args:
            command: Datos validados para crear la orden

        Returns:
            OrderCreatedResult con los datos de la orden creada

        Raises:
            ValueError: Si algún dato del comando es inválido en dominio
        """
        logger.info(
            "CreateOrder iniciado — cliente: %s, items: %d",
            command.customer_email,
            len(command.items),
        )

        # 1. Construir entidades de dominio
        customer = Customer(
            name=command.customer_name,
            email=Email(command.customer_email),
            phone=command.customer_phone,
        )

        domain_items = [
            OrderItem(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=Money(
                    amount=item.unit_price,
                    currency=item.currency,
                ),
            )
            for item in command.items
        ]

        order_id = OrderId.generate(command.sequence_number)

        order = Order(
            order_id=order_id,
            customer=customer,
            items=domain_items,
            notes=command.notes,
        )

        # 2. Persistir — el caso de uso no sabe si es SQL o memoria
        self._repo.save(order)  # type: ignore[attr-defined]

        logger.info(
            "CreateOrder persistido — order_id: %s, total: %s",
            order.order_id,
            order.total,
        )

        # 3. Notificar — el caso de uso no sabe si es HTTP o email
        try:
            self._notifier.order_created(
                order_id=str(order.order_id),
                customer_email=str(order.customer.email),
                total=float(order.total.amount),
            )
        except Exception as exc:
            # La notificación nunca debe romper el flujo principal
            logger.warning("Notificación fallida (no crítico): %s", exc)

        # 4. Construir y retornar DTO de resultado
        result = OrderCreatedResult(
            order_id=str(order.order_id),
            customer_name=order.customer.name,
            customer_email=str(order.customer.email),
            status=order.status.value,
            total=order.total.amount,
            items=[
                OrderItemResult(
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price.amount,
                    subtotal=item.subtotal.amount,
                    currency=item.unit_price.currency,
                )
                for item in order.items
            ],
            notes=order.notes,
        )

        logger.info("CreateOrder completado — %s", result.order_id)
        return result
