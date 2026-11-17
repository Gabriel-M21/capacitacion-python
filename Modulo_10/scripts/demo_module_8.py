"""
Pruebas del repositorio de órdenes - Módulo 8
Usa SQLite en memoria para no tocar la base de datos real.
"""

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from order_management.domain.entities import Customer, Order, OrderItem
from order_management.domain.value_objects import Email, Money, OrderId, OrderStatus
from order_management.infrastructure.db.repositories.order_repository import (
    OrderNotFoundError,
    OrderRepository,
)
from order_management.infrastructure.db.session import get_in_memory_session

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Sesión SQLite en memoria con tablas creadas y destruidas por prueba."""
    gen = get_in_memory_session()
    db = next(gen)
    yield db
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.fixture
def repo(session: Session) -> OrderRepository:
    return OrderRepository(session)


@pytest.fixture
def sample_order() -> Order:
    """Orden de dominio con 2 items para usar en pruebas."""
    customer = Customer(
        name="Juan Pérez",
        email=Email("juan.perez@example.com"),
        phone="+52 55 1234 5678",
    )
    items = [
        OrderItem(
            product_name="Laptop Dell XPS 15",
            quantity=1,
            unit_price=Money(Decimal("1299.99"), "USD"),
        ),
        OrderItem(
            product_name="Mouse Logitech MX Master",
            quantity=2,
            unit_price=Money(Decimal("49.99"), "USD"),
        ),
    ]
    return Order(
        order_id=OrderId.generate(1),
        customer=customer,
        items=items,
    )


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------


def test_save_persists_order(repo: OrderRepository, sample_order: Order) -> None:
    """save() guarda la orden y se puede recuperar por order_id."""
    repo.save(sample_order)

    recovered = repo.get_by_order_id("ORD-00001")

    assert recovered.order_id == sample_order.order_id
    assert recovered.customer.name == "Juan Pérez"
    assert recovered.customer.email == Email("juan.perez@example.com")
    assert len(recovered.items) == 2
    assert recovered.total == Money(Decimal("1399.97"), "USD")


def test_save_reuses_existing_user(repo: OrderRepository, sample_order: Order) -> None:
    """save() reutiliza el UserModel si el email ya existe."""

    from order_management.infrastructure.db.models import UserModel

    repo.save(sample_order)

    # Segunda orden del mismo cliente
    order2 = Order(
        order_id=OrderId.generate(2),
        customer=sample_order.customer,
        items=sample_order.items[:1],
    )
    repo.save(order2)

    user_count = repo._session.query(UserModel).count()
    assert user_count == 1


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------


def test_get_by_order_id_raises_if_not_found(repo: OrderRepository) -> None:
    """get_by_order_id() lanza OrderNotFoundError si no existe."""
    with pytest.raises(OrderNotFoundError):
        repo.get_by_order_id("ORD-99999")


def test_list_by_customer_email_returns_orders(repo: OrderRepository, sample_order: Order) -> None:
    """list_by_customer_email() devuelve todas las órdenes del cliente."""
    repo.save(sample_order)

    order2 = Order(
        order_id=OrderId.generate(2),
        customer=sample_order.customer,
        items=sample_order.items[:1],
    )
    repo.save(order2)

    orders = repo.list_by_customer_email("juan.perez@example.com")
    assert len(orders) == 2


def test_list_by_customer_email_returns_empty_for_unknown(repo: OrderRepository) -> None:
    """list_by_customer_email() devuelve lista vacía si el email no existe."""
    orders = repo.list_by_customer_email("noexiste@example.com")
    assert orders == []


def test_list_all_returns_all_orders(repo: OrderRepository, sample_order: Order) -> None:
    """list_all() devuelve todas las órdenes guardadas."""
    repo.save(sample_order)

    order2 = Order(
        order_id=OrderId.generate(2),
        customer=sample_order.customer,
        items=sample_order.items[:1],
    )
    repo.save(order2)

    all_orders = repo.list_all()
    assert len(all_orders) == 2


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


def test_update_status_valid_transition(repo: OrderRepository, sample_order: Order) -> None:
    """update_status() aplica transiciones válidas correctamente."""
    repo.save(sample_order)

    updated = repo.update_status("ORD-00001", OrderStatus.CONFIRMED)
    assert updated.status == OrderStatus.CONFIRMED

    # Verificar que persiste en DB
    recovered = repo.get_by_order_id("ORD-00001")
    assert recovered.status == OrderStatus.CONFIRMED


def test_update_status_invalid_transition_raises(
    repo: OrderRepository, sample_order: Order
) -> None:
    """update_status() respeta las reglas de transición del dominio."""
    repo.save(sample_order)

    with pytest.raises(ValueError, match="Transición inválida"):
        repo.update_status("ORD-00001", OrderStatus.DELIVERED)


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


def test_delete_removes_order(repo: OrderRepository, sample_order: Order) -> None:
    """delete() elimina la orden y sus items (cascade)."""
    repo.save(sample_order)
    repo.delete("ORD-00001")

    with pytest.raises(OrderNotFoundError):
        repo.get_by_order_id("ORD-00001")


def test_delete_raises_if_not_found(repo: OrderRepository) -> None:
    """delete() lanza OrderNotFoundError si la orden no existe."""
    with pytest.raises(OrderNotFoundError):
        repo.delete("ORD-99999")


def test_money_reconstructed_correctly(repo: OrderRepository, sample_order: Order) -> None:
    """Money se reconstruye correctamente desde las columnas unit_price + currency."""
    repo.save(sample_order)

    recovered = repo.get_by_order_id("ORD-00001")
    laptop = next(i for i in recovered.items if "Laptop" in i.product_name)

    assert laptop.unit_price.amount == Decimal("1299.99")
    assert laptop.unit_price.currency == "USD"
    assert laptop.subtotal == Money(Decimal("1299.99"), "USD")
