"""
Caso de uso CreateOrder v2 - Módulo 16: Arquitectura Limpia

Versión actualizada que incorpora:
  - Unit of Work para atomicidad de la transacción
  - Eventos de dominio (OrderCreated) publicados al EventBus
  - Presenter para formatear el resultado según el canal de salida

Flujo:
  CreateOrderCommand
      ↓  construir entidades de dominio
      with uow:
          ↓  uow.orders.save(order)
          ↓  uow.add_event(OrderCreated(...))
          ↓  uow.commit()
      ↓  event_bus.publish_all(uow.collect_events())
      ↓  presenter.present(result)
      ↓
  Formato de salida (JSON, CLI, schema Pydantic, etc.)
"""

import logging
from typing import Any

from order_management.application.dtos import (
    CreateOrderCommand,
    OrderCreatedResult,
    OrderItemResult,
)
from order_management.application.event_bus import EventBus
from order_management.application.presenters import JsonPresenter, OrderPresenterPort
from order_management.application.unit_of_work import UnitOfWorkPort
from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.events import OrderCreated
from order_management.domain.value_objects import Email, Money, OrderId

logger = logging.getLogger(__name__)


class CreateOrderUseCase:
    """
    Caso de uso: Crear una nueva orden de compra.

    Versión Módulo 16 — incorpora UoW, eventos y Presenter.

    DIP: depende de UnitOfWorkPort, EventBus y OrderPresenterPort.
    SRP: su única razón de cambiar es la lógica de creación de órdenes.
    OCP: añadir un nuevo presenter o handler de evento no modifica este código.
    """

    def __init__(
        self,
        uow: UnitOfWorkPort,
        event_bus: EventBus,
        presenter: OrderPresenterPort | None = None,
    ) -> None:
        """
        Args:
            uow:       Unit of Work que agrupa repositorio y transacción
            event_bus: Bus para publicar eventos de dominio
            presenter: Formatea el resultado (default: JsonPresenter)
        """
        self._uow = uow
        self._bus = event_bus
        self._presenter = presenter or JsonPresenter()

    def execute(self, command: CreateOrderCommand) -> Any:
        """
        Ejecuta el caso de uso CreateOrder con UoW y eventos.

        Args:
            command: Datos validados para crear la orden

        Returns:
            Resultado formateado por el Presenter

        Raises:
            ValueError: Si algún dato del comando es inválido en dominio
        """
        logger.info(
            "CreateOrder (v2) iniciado — cliente: %s, items: %d",
            command.customer_email,
            len(command.items),
        )

        # 1. Construir entidades de dominio (sin infraestructura)
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

        # 2. Persistir con Unit of Work (atómico)
        with self._uow:
            self._uow.orders.save(order)  # type: ignore[attr-defined]

            # 3. Generar evento de dominio
            event = OrderCreated(
                order_id=str(order.order_id),
                customer_email=str(order.customer.email),
                customer_name=order.customer.name,
                total=order.total.amount,
                item_count=order.item_count,
                status=order.status.value,
            )

            # Acumular evento en el UoW para publicarlo después del commit
            if hasattr(self._uow, "add_event"):
                self._uow.add_event(event)  # type: ignore[attr-defined]

            self._uow.commit()

        # 4. Publicar eventos DESPUÉS del commit (no dentro de la transacción)
        pending_events = self._uow.collect_events()
        self._bus.publish_all(pending_events)

        logger.info(
            "CreateOrder completado — %s, eventos publicados: %d",
            order.order_id,
            len(pending_events),
        )

        # 5. Construir DTO de resultado
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

        # 6. Formatear con el Presenter y retornar
        return self._presenter.present(result)
