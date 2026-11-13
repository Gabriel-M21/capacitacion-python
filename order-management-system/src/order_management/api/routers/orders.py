"""
Router de órdenes - Módulo 9: APIs web con FastAPI
CRUD completo de órdenes con autenticación JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from order_management.api.dependencies import get_current_user, get_db
from order_management.domain.value_objects import OrderId, OrderStatus
from order_management.infrastructure.db.repositories.order_repository import (
    OrderNotFoundError,
    OrderRepository,
)
from order_management.mappers.order_mapper import OrderMapper
from order_management.schemas.schemas import OrderIn, OrderOut

router = APIRouter(
    prefix="/orders",
    tags=["Órdenes"],
    dependencies=[Depends(get_current_user)],  # todos los endpoints requieren JWT
)

# Contador simple de secuencia para OrderId en el lab
# En producción vendría de la DB (secuencia o UUID)
_sequence: list[int] = [0]


def _next_order_id() -> OrderId:
    _sequence[0] += 1
    return OrderId.generate(_sequence[0])


class StatusUpdate(BaseModel):
    """Body para cambiar el estado de una orden."""

    status: str


# ---------------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[OrderOut],
    summary="Listar todas las órdenes",
)
def list_orders(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> list[OrderOut]:
    """Devuelve todas las órdenes registradas en el sistema."""
    repo = OrderRepository(db)
    orders = repo.list_all()
    return [OrderMapper.to_api_order(o) for o in orders]


# ---------------------------------------------------------------------------
# GET /orders/{order_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Obtener una orden por ID",
)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """
    Busca y devuelve una orden por su ID (formato ORD-XXXXX).

    - **order_id**: ID de la orden, ej. ORD-00001
    """
    repo = OrderRepository(db)
    try:
        order = repo.get_by_order_id(order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la orden '{order_id}'",
        ) from None
    return OrderMapper.to_api_order(order)


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva orden",
)
def create_order(
    order_in: OrderIn,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """
    Crea una nueva orden validando cliente e items con Pydantic.
    Devuelve la orden creada con su ID, total y estado inicial.
    """
    order_id = _next_order_id()
    order = OrderMapper.to_domain_order(order_in, order_id)

    repo = OrderRepository(db)
    repo.save(order)

    return OrderMapper.to_api_order(order)


# ---------------------------------------------------------------------------
# PATCH /orders/{order_id}/status
# ---------------------------------------------------------------------------


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Cambiar estado de una orden",
)
def update_order_status(
    order_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """
    Cambia el estado de una orden validando la transición en el dominio.

    **Transiciones válidas:**
    - pending → confirmed | cancelled
    - confirmed → processing | cancelled
    - processing → shipped | cancelled
    - shipped → delivered
    """
    try:
        new_status = OrderStatus(body.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Estado inválido: '{body.status}'",
        ) from None

    repo = OrderRepository(db)
    try:
        updated = repo.update_status(order_id, new_status)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la orden '{order_id}'",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None

    return OrderMapper.to_api_order(updated)


# ---------------------------------------------------------------------------
# DELETE /orders/{order_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una orden",
)
def delete_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> None:
    """
    Elimina una orden y todos sus items (cascade).

    Devuelve **204 No Content** si se eliminó correctamente.
    """
    repo = OrderRepository(db)
    try:
        repo.delete(order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la orden '{order_id}'",
        ) from None
