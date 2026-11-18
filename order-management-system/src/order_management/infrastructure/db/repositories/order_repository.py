"""
Repositorio de órdenes - Módulo 8: Acceso a datos y ORM
Traduce entre entidades de dominio (Order, Customer, OrderItem)
y modelos ORM (OrderModel, UserModel, OrderItemModel).

Aquí es donde ORM y dominio se tocan; en ningún otro sitio.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus
from order_management.infrastructure.db.models import OrderItemModel, OrderModel, UserModel


class OrderNotFoundError(Exception):
    """La orden solicitada no existe en la base de datos."""


class OrderRepository:
    """CRUD de órdenes usando SQLAlchemy ORM."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def save(self, order: Order) -> OrderModel:
        """
        Persiste una Order de dominio en la base de datos.

        Si el usuario (por email) ya existe, lo reutiliza.
        Si la orden (por order_id) ya existe, la actualiza.

        Args:
            order: Entidad de dominio a persistir

        Returns:
            Modelo ORM guardado
        """
        # 1. Buscar o crear el UserModel
        user_model = (
            self._session.query(UserModel).filter_by(email=str(order.customer.email)).first()
        )
        if user_model is None:
            user_model = UserModel(
                name=order.customer.name,
                email=str(order.customer.email),
                phone=order.customer.phone,
            )
            self._session.add(user_model)
            self._session.flush()  # obtener user_model.id antes de usarlo

        # 2. Buscar o crear el OrderModel
        order_model = (
            self._session.query(OrderModel).filter_by(order_id=str(order.order_id)).first()
        )
        if order_model is None:
            order_model = OrderModel(
                order_id=str(order.order_id),
                status=order.status.value,
                created_at=order.created_at,
                notes=order.notes,
                user_id=user_model.id,
            )
            self._session.add(order_model)
            self._session.flush()
        else:
            order_model.status = order.status.value
            order_model.notes = order.notes

        # 3. Reemplazar items (delete + insert para simplicidad)
        for existing_item in order_model.items:
            self._session.delete(existing_item)
        self._session.flush()

        for item in order.items:
            item_model = OrderItemModel(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=float(item.unit_price.amount),
                currency=item.unit_price.currency,
                order_id=order_model.id,
            )
            self._session.add(item_model)

        self._session.flush()
        return order_model

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_by_order_id(self, order_id: str) -> Order:
        """
        Busca una orden por su order_id (formato ORD-XXXXX).

        Args:
            order_id: ID de la orden

        Returns:
            Entidad de dominio Order

        Raises:
            OrderNotFoundError: Si no existe la orden
        """
        order_model = self._session.query(OrderModel).filter_by(order_id=order_id).first()
        if order_model is None:
            raise OrderNotFoundError(f"No existe la orden '{order_id}'")

        return self._to_domain(order_model)

    def list_by_customer_email(self, email: str) -> list[Order]:
        """
        Lista todas las órdenes de un cliente por email.

        Args:
            email: Email del cliente

        Returns:
            Lista de entidades Order (vacía si no hay órdenes)
        """
        user_model = self._session.query(UserModel).filter_by(email=email).first()
        if user_model is None:
            return []

        return [self._to_domain(o) for o in user_model.orders]

    def list_all(self) -> list[Order]:
        """
        Lista todas las órdenes en la base de datos.

        Returns:
            Lista de entidades Order
        """
        order_models = self._session.query(OrderModel).all()
        return [self._to_domain(o) for o in order_models]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_status(self, order_id: str, new_status: OrderStatus) -> Order:
        """
        Cambia el estado de una orden validando la transición en dominio.

        Args:
            order_id: ID de la orden
            new_status: Nuevo estado

        Returns:
            Order actualizada

        Raises:
            OrderNotFoundError: Si no existe la orden
            ValueError: Si la transición de estado no es válida
        """
        order = self.get_by_order_id(order_id)
        order.change_status(new_status)  # valida la transición en dominio
        self.save(order)
        return order

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete(self, order_id: str) -> None:
        """
        Elimina una orden por su order_id.

        Args:
            order_id: ID de la orden a eliminar

        Raises:
            OrderNotFoundError: Si no existe la orden
        """
        order_model = self._session.query(OrderModel).filter_by(order_id=order_id).first()
        if order_model is None:
            raise OrderNotFoundError(f"No existe la orden '{order_id}'")

        self._session.delete(order_model)
        self._session.flush()

    # ------------------------------------------------------------------
    # PRIVADO: traducción ORM → dominio
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(order_model: OrderModel) -> Order:
        """
        Convierte un OrderModel (ORM) a una Order (dominio).

        Reconstruye:
          - Email desde string
          - Money desde (unit_price, currency)
          - OrderId desde string
          - OrderStatus desde string (.value)
        """
        customer = Customer(
            name=order_model.user.name,
            email=Email(order_model.user.email),
            phone=order_model.user.phone,
        )

        items = [
            OrderItem(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=Money(
                    amount=Decimal(str(item.unit_price)),
                    currency=item.currency,
                ),
            )
            for item in order_model.items
        ]

        return Order(
            order_id=OrderId(order_model.order_id),
            customer=customer,
            items=items,
            status=OrderStatus(order_model.status),
            created_at=order_model.created_at,
            notes=order_model.notes,
        )
