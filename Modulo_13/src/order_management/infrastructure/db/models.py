"""
Modelos ORM - Módulo 8: Acceso a datos y ORM
Mapea las entidades de dominio (Customer, Order, OrderItem) a tablas SQL.

Regla: estos modelos NO importan nada de domain/. La traducción
       entre ORM y dominio ocurre exclusivamente en los repositorios.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from order_management.infrastructure.db.base import Base


class UserModel(Base):
    """
    Tabla 'users' — corresponde a la entidad Customer del dominio.

    Se llama UserModel (no CustomerModel) para seguir la convención
    habitual de DB donde la tabla de personas/cuentas se llama 'users'.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")

    # Relación 1-N con órdenes
    orders: Mapped[list["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"UserModel(id={self.id}, name={self.name!r}, email={self.email!r})"


class OrderModel(Base):
    """
    Tabla 'orders' — corresponde a la entidad Order del dominio.

    - order_id guarda el string con formato ORD-XXXXX (Value Object OrderId)
    - status guarda el .value del enum OrderStatus
    - user_id es FK a users.id
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # FK a users
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")

    # Relación 1-N con items
    items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"OrderModel(id={self.id}, order_id={self.order_id!r}, "
            f"status={self.status!r}, items={len(self.items)})"
        )


class OrderItemModel(Base):
    """
    Tabla 'order_items' — corresponde a la entidad OrderItem del dominio.

    Money se descompone en dos columnas:
      - unit_price: Numeric(12, 2)
      - currency:   String(3)   → código ISO 4217 (ej. 'USD')

    Al leer desde DB, el repositorio reconstruye Money(amount, currency).
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # FK a orders
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="items")

    def __repr__(self) -> str:
        return (
            f"OrderItemModel(id={self.id}, product_name={self.product_name!r}, "
            f"quantity={self.quantity}, unit_price={self.unit_price} {self.currency})"
        )
