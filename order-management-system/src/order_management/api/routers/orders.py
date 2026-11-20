"""
Router de órdenes - Proyecto Final Integrador
CRUD completo + todas las funcionalidades del learning path:
    CRUD básico con JWT
    Pricing strategies (descuentos por volumen, temporada, VIP)
    Comparación async vs sync (fetcher de catálogo)
    SOLID — OrderService con repositorio inyectado
    Patrones — Strategy, Builder, Decorator (caché)
    ML — inferencia con clasificador joblib
    Hexagonal — CreateOrderUseCase con UoW y eventos
    Arquitectura Limpia — eventos + presenters
    Ingesta CSV con pandas y métricas
"""

import asyncio
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker as sm

from order_management.api.dependencies import get_current_user, get_db
from order_management.application.dtos import CreateOrderCommand, OrderItemCommand
from order_management.application.event_bus import EventBus
from order_management.application.presenters import (
    AuditPresenter,
    CliPresenter,
    JsonPresenter,
    OrderPresenterPort,
)
from order_management.application.use_cases.create_order import CreateOrderUseCase
from order_management.domain.events import OrderCreated
from order_management.domain.pricing import volume_discount
from order_management.domain.strategies import (
    MaxDiscountStrategy,
    NoDiscountStrategy,
    SeasonalDiscountStrategy,
    VIPDiscountStrategy,
    VolumeDiscountStrategy,
)
from order_management.domain.value_objects import OrderId, OrderStatus
from order_management.infrastructure.db.repositories.order_repository import (
    OrderNotFoundError,
    OrderRepository,
)
from order_management.infrastructure.db.session import engine
from order_management.infrastructure.uow.sqlalchemy_uow import SqlAlchemyUnitOfWork
from order_management.mappers.order_mapper import OrderMapper
from order_management.schemas.schemas import OrderIn, OrderOut
from order_management.services.order_builder import OrderBuilder

router = APIRouter(
    prefix="/orders",
    tags=["Órdenes"],
    dependencies=[Depends(get_current_user)],
)

_sequence: list[int] = [0]

DATA_DIR = Path("data")
MODEL_PATH = DATA_DIR / "output" / "order_classifier.joblib"
CSV_PATH = DATA_DIR / "orders_extended.csv"


def _next_order_id() -> OrderId:
    _sequence[0] += 1
    return OrderId.generate(_sequence[0])


# ---------------------------------------------------------------------------
# Modelos de request/response adicionales
# ---------------------------------------------------------------------------


class StatusUpdate(BaseModel):
    status: str


class DiscountRequest(BaseModel):
    strategy: str = "volume"
    item_count: int = 1
    total: float = 0.0
    email: str = ""
    vip_emails: list[str] = []
    seasonal_pct: float = 10.0


class BuilderOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    notes: str | None = None
    items: list[dict[str, Any]] = []
    express: bool = False


class InferenceRequest(BaseModel):
    order_total: float
    item_count: int
    hour: int = 10
    day_of_week: int = 1
    month: int = 6


class UseCaseOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    items: list[dict[str, Any]]
    notes: str | None = None
    presenter: str = "json"


# ===========================================================================
# CRUD básico
# ===========================================================================


@router.get("", response_model=list[OrderOut], summary="Listar todas las órdenes")
def list_orders(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> list[OrderOut]:
    """Devuelve todas las órdenes registradas."""
    repo = OrderRepository(db)
    return [OrderMapper.to_api_order(o) for o in repo.list_all()]


@router.get("/{order_id}", response_model=OrderOut, summary="Obtener una orden por ID")
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """Busca una orden por su ID (formato ORD-XXXXX)."""
    repo = OrderRepository(db)
    try:
        return OrderMapper.to_api_order(repo.get_by_order_id(order_id))
    except OrderNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe '{order_id}'") from None


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva orden ( 9)",
)
def create_order(
    order_in: OrderIn,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """Crea una orden usando el flujo clásico: Pydantic → Mapper → Repositorio."""
    order_id = _next_order_id()
    order = OrderMapper.to_domain_order(order_in, order_id)
    repo = OrderRepository(db)
    repo.save(order)
    return OrderMapper.to_api_order(order)


@router.patch("/{order_id}/status", response_model=OrderOut, summary="Cambiar estado")
def update_order_status(
    order_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> OrderOut:
    """Cambia el estado validando la transición en el dominio."""
    try:
        new_status = OrderStatus(body.status)
    except ValueError:
        raise HTTPException(422, f"Estado inválido: '{body.status}'") from None
    repo = OrderRepository(db)
    try:
        updated = repo.update_status(order_id, new_status)
    except OrderNotFoundError:
        raise HTTPException(404, f"No existe '{order_id}'") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return OrderMapper.to_api_order(updated)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una orden")
def delete_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> None:
    """Elimina una orden y todos sus items (cascade)."""
    repo = OrderRepository(db)
    try:
        repo.delete(order_id)
    except OrderNotFoundError:
        raise HTTPException(404, f"No existe '{order_id}'") from None


# ===========================================================================
#  10 — TDD: volume_discount directo
# ===========================================================================


@router.get(
    "/tools/volume-discount/{item_count}",
    tags=["Herramientas del proyecto"],
    summary=" 10 — Descuento por volumen",
)
def get_volume_discount(item_count: int) -> dict[str, Any]:
    """
    Calcula el descuento por volumen según las reglas de negocio (TDD).
    - 1-2 items → 0%
    - 3-5 items → 5%
    - 6-9 items → 10%
    - 10+ items → 15%
    """
    try:
        pct = volume_discount(item_count)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    return {
        "item_count": item_count,
        "discount_percentage": float(pct),
        "factor": float((Decimal("100") - pct) / Decimal("100")),
        "module": " 10 — TDD + Hypothesis",
    }


# ===========================================================================
#  11 — Concurrencia: async vs sync
# ===========================================================================


@router.get(
    "/tools/concurrency-benchmark",
    tags=["Herramientas del proyecto"],
    summary=" 11 — Benchmark async vs sync",
)
def concurrency_benchmark(
    n_orders: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """
    Compara el tiempo de procesamiento secuencial vs concurrente
    usando las órdenes existentes en la DB.
    Demuestra el concepto del  11 sin requerir Smocker.
    """
    import math

    def cpu_task(n: int) -> float:
        """Tarea CPU-bound: calcular raíces."""
        return sum(math.sqrt(i) for i in range(n))

    async def async_tasks(count: int) -> float:
        """Simula I/O asíncrono con asyncio.sleep."""

        async def single() -> float:
            await asyncio.sleep(0.001)
            return cpu_task(100)

        start = time.perf_counter()
        await asyncio.gather(*[single() for _ in range(count)])
        return time.perf_counter() - start

    # Secuencial
    t0 = time.perf_counter()
    for _ in range(n_orders):
        time.sleep(0.001)
        cpu_task(100)
    sync_time = time.perf_counter() - t0

    # Asíncrono
    async_time = asyncio.run(async_tasks(n_orders))

    speedup = round(sync_time / async_time, 2) if async_time > 0 else 0

    return {
        "n_tasks": n_orders,
        "sync_time_s": round(sync_time, 4),
        "async_time_s": round(async_time, 4),
        "speedup": speedup,
        "conclusion": (
            "asyncio es más rápido para I/O-bound"
            if speedup > 1
            else "overhead de asyncio supera la ganancia para tareas pequeñas"
        ),
        "module": " 11 — Concurrencia y rendimiento",
    }


# ===========================================================================
#  12 — SOLID: OrderValidator
# ===========================================================================


@router.post(
    "/tools/validate",
    tags=["Herramientas del proyecto"],
    summary=" 12 — SOLID: Validar orden sin persistir",
)
def validate_order(order_data: dict[str, Any]) -> dict[str, Any]:
    """
    Valida una orden usando OrderValidator (SRP del  12).
    No persiste — solo aplica las reglas de validación.
    """
    from order_management.services.order_validator import OrderValidator

    validator = OrderValidator()
    ok, msg = validator.validate(order_data)
    return {
        "valid": ok,
        "message": msg if not ok else "Orden válida",
        "module": " 12 — SOLID (SRP + DIP)",
    }


# ===========================================================================
#  13 — Patrones: Strategy de precios
# ===========================================================================


@router.post(
    "/tools/pricing-strategy",
    tags=["Herramientas del proyecto"],
    summary=" 13 — Patrones: Strategy de descuentos",
)
def apply_pricing_strategy(request: DiscountRequest) -> dict[str, Any]:
    """
    Aplica diferentes estrategias de descuento (Strategy Pattern).
    Estrategias disponibles: volume, seasonal, vip, max, none.
    """
    order_data: dict[str, Any] = {
        "email": request.email,
        "items": [{"product_name": "item", "quantity": 1, "price": request.total}],
    }

    strategies: dict[str, Any] = {
        "none": NoDiscountStrategy(),
        "volume": VolumeDiscountStrategy(),
        "seasonal": SeasonalDiscountStrategy(Decimal(str(request.seasonal_pct))),
        "vip": VIPDiscountStrategy(
            vip_emails=set(request.vip_emails),
            vip_discount=Decimal("20"),
        ),
        "max": MaxDiscountStrategy(
            [
                VolumeDiscountStrategy(),
                SeasonalDiscountStrategy(Decimal(str(request.seasonal_pct))),
            ]
        ),
    }

    if request.strategy not in strategies:
        raise HTTPException(
            422,
            f"Estrategia inválida. Válidas: {list(strategies.keys())}",
        )

    # Para volume usamos item_count directamente
    if request.strategy == "volume":
        pct = volume_discount(max(request.item_count, 1))
    else:
        pct = strategies[request.strategy].calculate_discount(order_data)

    factor = (Decimal("100") - pct) / Decimal("100")
    total_original = Decimal(str(request.total))
    total_final = total_original * factor

    return {
        "strategy": request.strategy,
        "item_count": request.item_count,
        "total_original": float(total_original),
        "discount_percentage": float(pct),
        "total_final": float(total_final),
        "saving": float(total_original - total_final),
        "module": " 13 — Patrones de diseño (Strategy)",
    }


# ===========================================================================
#  13 — Builder: construir orden paso a paso
# ===========================================================================


@router.post(
    "/tools/builder",
    tags=["Herramientas del proyecto"],
    summary=" 13 — Patrones: Builder de órdenes",
    status_code=status.HTTP_201_CREATED,
)
def create_order_with_builder(
    request: BuilderOrderRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Construye y persiste una orden usando el Builder Pattern ( 13).
    Si express=true usa el factory method OrderBuilder.express_order().
    """
    order_id = _next_order_id()

    if request.express:
        builder = OrderBuilder.express_order(
            order_id=order_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
        )
    else:
        builder = OrderBuilder(order_id=order_id).with_customer(
            request.customer_name,
            request.customer_email,
            request.customer_phone,
        )
        if request.notes:
            builder = builder.with_notes(request.notes)

    for item in request.items:
        builder = builder.add_item(
            product_name=str(item.get("product_name", "")),
            quantity=int(item.get("quantity", 1)),
            unit_price=float(item.get("unit_price", 0)),
        )

    try:
        order = builder.build()
    except Exception as exc:
        raise HTTPException(422, str(exc)) from None

    repo = OrderRepository(db)
    repo.save(order)

    return {
        "order_id": str(order.order_id),
        "customer": order.customer.name,
        "status": order.status.value,
        "total": float(order.total.amount),
        "item_count": order.item_count,
        "notes": order.notes,
        "express": request.express,
        "module": " 13 — Patrones de diseño (Builder)",
    }


# ===========================================================================
#  14 — ML: inferencia con joblib
# ===========================================================================


@router.post(
    "/tools/ml-inference",
    tags=["Herramientas del proyecto"],
    summary=" 14 — ML: Predecir estado de una orden",
)
def ml_inference(request: InferenceRequest) -> dict[str, Any]:
    """
    Predice el estado probable de una orden usando el clasificador
    RandomForest entrenado en el  14 y guardado con joblib.
    Features: order_total, item_count, hour, day_of_week, month.
    """
    if not MODEL_PATH.exists():
        raise HTTPException(
            404,
            f"Modelo no encontrado en {MODEL_PATH}. "
            "Ejecuta primero: poetry run python scripts/demo_module_14.py",
        )

    try:
        import joblib  # type: ignore[import-untyped]
        import numpy as np

        bundle = joblib.load(MODEL_PATH)
        clf = bundle["clf"]
        le = bundle["le"]

        X = np.array(
            [
                [
                    request.order_total,
                    request.item_count,
                    request.hour,
                    request.day_of_week,
                    request.month,
                ]
            ]
        )

        pred_encoded = clf.predict(X)[0]
        probabilities = clf.predict_proba(X)[0]
        pred_label = le.inverse_transform([pred_encoded])[0]
        confidence = float(probabilities.max())

        all_probs = {
            label: round(float(prob), 4)
            for label, prob in zip(le.classes_, probabilities, strict=True)
        }

        return {
            "prediction": pred_label,
            "confidence": round(confidence, 4),
            "all_probabilities": all_probs,
            "input": {
                "order_total": request.order_total,
                "item_count": request.item_count,
                "hour": request.hour,
                "day_of_week": request.day_of_week,
                "month": request.month,
            },
            "module": " 14 — Ciencia de datos (scikit-learn + joblib)",
        }
    except Exception as exc:
        raise HTTPException(500, f"Error en inferencia: {exc}") from exc


# ===========================================================================
#  14 — Pandas: métricas del CSV
# ===========================================================================


@router.get(
    "/tools/csv-metrics",
    tags=["Herramientas del proyecto"],
    summary=" 14 — Pandas: métricas del CSV de órdenes",
)
def csv_metrics() -> dict[str, Any]:
    """
    Carga orders_extended.csv con Pandas, lo limpia y devuelve métricas
    agregadas: revenue, top productos, distribución de estados.
    """
    if not CSV_PATH.exists():
        raise HTTPException(
            404,
            f"CSV no encontrado: {CSV_PATH}. Asegúrate de tener data/orders_extended.csv",
        )

    try:
        import pandas as pd  # type: ignore[import-untyped]

        df = pd.read_csv(CSV_PATH, encoding="utf-8")

        # Limpieza
        df = df.dropna(subset=["order_id", "customer_name", "email", "product_name"])
        df = df[df["price"] > 0]
        df = df[df["quantity"] > 0]
        df = df[df["status"].isin(["pending", "confirmed", "shipped", "delivered", "cancelled"])]

        df["subtotal"] = df["price"] * df["quantity"]

        # Métricas por orden
        order_totals = df.groupby("order_id")["subtotal"].sum()

        # Top 5 productos por revenue
        top_products = (
            df.groupby("product_name")["subtotal"].sum().sort_values(ascending=False).head(5)
        )

        # Distribución de estados (por orden única)
        status_dist = df.drop_duplicates("order_id")["status"].value_counts().to_dict()

        return {
            "total_rows": len(df),
            "unique_orders": int(df["order_id"].nunique()),
            "unique_customers": int(df["email"].nunique()),
            "total_revenue": round(float(order_totals.sum()), 2),
            "avg_order_value": round(float(order_totals.mean()), 2),
            "max_order_value": round(float(order_totals.max()), 2),
            "status_distribution": status_dist,
            "top_5_products_by_revenue": {k: round(float(v), 2) for k, v in top_products.items()},
            "module": " 14 — Pandas + Ciencia de datos",
        }
    except Exception as exc:
        raise HTTPException(500, f"Error procesando CSV: {exc}") from exc


# ===========================================================================
#  15 — Hexagonal: CreateOrderUseCase con UoW + EventBus
# ===========================================================================


@router.post(
    "/tools/use-case",
    tags=["Herramientas del proyecto"],
    summary=" 15/16 — Hexagonal: CreateOrder con UoW + EventBus + Presenter",
    status_code=status.HTTP_201_CREATED,
)
def create_order_use_case(
    request: UseCaseOrderRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Crea una orden usando el caso de uso completo del  15/16:
    - Unit of Work (SqlAlchemyUnitOfWork) para atomicidad
    - EventBus para publicar OrderCreated
    - Presenter configurable: json | cli | audit

    Presenters disponibles: json, cli, audit
    """
    events_captured: list[str] = []

    bus = EventBus()
    bus.register(
        OrderCreated,
        lambda e: events_captured.append(
            f"OrderCreated: {e.order_id} — {e.customer_email} — ${e.total:.2f}"
        ),
    )

    presenters: dict[str, OrderPresenterPort] = {
        "json": JsonPresenter(),
        "cli": CliPresenter(),
        "audit": AuditPresenter(),
    }
    if request.presenter not in presenters:
        raise HTTPException(422, f"Presenter inválido. Válidos: {list(presenters.keys())}")

    Session = sm(bind=engine, autocommit=False, autoflush=False)
    uow = SqlAlchemyUnitOfWork(Session)

    command = CreateOrderCommand(
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        sequence_number=_sequence[0] + 1,
        notes=request.notes,
        items=[
            OrderItemCommand(
                product_name=str(i.get("product_name", "")),
                quantity=int(i.get("quantity", 1)),
                unit_price=Decimal(str(i.get("unit_price", 0))),
            )
            for i in request.items
        ],
    )

    try:
        uc = CreateOrderUseCase(
            uow=uow,
            event_bus=bus,
            presenter=presenters[request.presenter],
        )
        result = uc.execute(command)
        _sequence[0] += 1
    except Exception as exc:
        raise HTTPException(422, str(exc)) from exc

    return {
        "presenter_used": request.presenter,
        "result": result if isinstance(result, dict) else str(result),
        "events_published": events_captured,
        "module": " 15/16 — Arquitectura Hexagonal/Limpia (UoW + EventBus + Presenter)",
    }


# ===========================================================================
# RESUMEN: todos los endpoints disponibles
# ===========================================================================


@router.get(
    "/tools/capabilities",
    tags=["Herramientas del proyecto"],
    summary="Resumen de todas las capacidades expuestas",
)
def capabilities() -> dict[str, Any]:
    """Lista todos los endpoints de demostración disponibles con su  origen."""
    return {
        "crud_basico": {
            "GET /orders": "Listar órdenes",
            "POST /orders": "Crear orden (Pydantic + Mapper)",
            "GET /orders/{id}": "Obtener orden",
            "PATCH /orders/{id}/status": "Cambiar estado",
            "DELETE /orders/{id}": "Eliminar orden",
        },
        "herramientas": {
            "GET  /orders/tools/volume-discount/{n}": "TDD: descuento por volumen",
            "GET  /orders/tools/concurrency-benchmark": "Async vs sync benchmark",
            "POST /orders/tools/validate": "SOLID: validar sin persistir",
            "POST /orders/tools/pricing-strategy": "Strategy de precios",
            "POST /orders/tools/builder": "Builder Pattern",
            "POST /orders/tools/ml-inference": "ML: predecir estado",
            "GET  /orders/tools/csv-metrics": "Pandas: métricas CSV",
            "POST /orders/tools/use-case": "Hexagonal: UoW+EventBus",
        },
        "documentacion": "http://localhost:8000/docs",
        "total_modulos_expuestos": 8,
    }
