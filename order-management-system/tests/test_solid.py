"""
Pruebas SOLID - Módulo 12
Verifica: DIP, LSP, SRP y OCP aplicados al refactor de OrderService.
"""

import json
from typing import Any

import pytest

from order_management.domain.ports import OrderRepositoryPort, OrderValidatorPort
from order_management.infrastructure.db.repositories.in_memory_order_repo import (
    InMemoryOrderRepository,
)
from order_management.infrastructure.db.repositories.json_order_repo import JsonFileOrderRepository
from order_management.services.order_service import OrderService
from order_management.services.order_validator import OrderValidator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_ORDER: dict[str, Any] = {
    "order_id": "ORD-001",
    "customer_name": "Juan Pérez",
    "email": "juan.perez@example.com",
    "status": "confirmed",
    "items": [
        {"product_name": "Laptop Dell XPS 15", "quantity": 1, "price": 1299.99},
        {"product_name": "Mouse Logitech", "quantity": 2, "price": 29.99},
    ],
}

INVALID_ORDER_NO_EMAIL: dict[str, Any] = {
    "order_id": "ORD-INV",
    "customer_name": "Sin Email",
    "status": "pending",
    "items": [{"product_name": "Producto X", "quantity": 1, "price": 10.0}],
}

INVALID_ORDER_EMPTY_NAME: dict[str, Any] = {
    "order_id": "ORD-INV2",
    "customer_name": "",
    "email": "test@example.com",
    "status": "pending",
    "items": [{"product_name": "Producto Y", "quantity": 1, "price": 20.0}],
}


@pytest.fixture
def valid_orders() -> list[dict[str, Any]]:
    return [
        VALID_ORDER,
        {
            "order_id": "ORD-002",
            "customer_name": "María García",
            "email": "maria.garcia@example.com",
            "status": "pending",
            "items": [
                {"product_name": "Teclado mecánico", "quantity": 2, "price": 129.50},
            ],
        },
    ]


@pytest.fixture
def mixed_orders(valid_orders) -> list[dict[str, Any]]:
    return valid_orders + [INVALID_ORDER_NO_EMAIL, INVALID_ORDER_EMPTY_NAME]


@pytest.fixture
def memory_repo(valid_orders) -> InMemoryOrderRepository:
    return InMemoryOrderRepository(orders=valid_orders)


@pytest.fixture
def service(memory_repo) -> OrderService:
    return OrderService(repository=memory_repo)


# ---------------------------------------------------------------------------
# DIP — OrderService depende del Protocol, no de implementaciones concretas
# ---------------------------------------------------------------------------


def test_dip_service_acepta_cualquier_implementacion_del_puerto(valid_orders):
    """
    DIP: OrderService funciona con cualquier objeto que cumpla
    OrderRepositoryPort, sin importar su clase concreta.
    """
    repo_memoria = InMemoryOrderRepository(orders=valid_orders)
    service_con_memoria = OrderService(repository=repo_memoria)

    resultado = service_con_memoria.process_orders()

    assert resultado["valid_orders"] == 2
    assert resultado["total_revenue"] == pytest.approx(1359.97 + 259.00, rel=1e-2)


def test_dip_port_es_un_protocol():
    """OrderRepositoryPort es un Protocol verificable en runtime."""
    repo = InMemoryOrderRepository()
    assert isinstance(repo, OrderRepositoryPort)


def test_dip_validator_port_es_un_protocol():
    """OrderValidatorPort es un Protocol verificable en runtime."""
    validator = OrderValidator()
    assert isinstance(validator, OrderValidatorPort)


# ---------------------------------------------------------------------------
# LSP — InMemoryOrderRepository y JsonFileOrderRepository son intercambiables
# ---------------------------------------------------------------------------


def test_lsp_mismo_resultado_con_memoria_y_json(valid_orders, tmp_path):
    """
    LSP: OrderService produce el mismo resultado independientemente
    de qué implementación de OrderRepositoryPort reciba.
    """
    # Con InMemory
    repo_mem = InMemoryOrderRepository(orders=valid_orders)
    result_mem = OrderService(repository=repo_mem).process_orders()

    # Con JsonFile (escribe ordenes en disco temporal)
    orders_file = tmp_path / "orders.json"
    summary_file = tmp_path / "summary.json"
    orders_file.write_text(json.dumps(valid_orders, ensure_ascii=False), encoding="utf-8")
    repo_json = JsonFileOrderRepository(
        orders_path=orders_file,
        summary_path=summary_file,
    )
    result_json = OrderService(repository=repo_json).process_orders()

    # El servicio debe producir el mismo resultado con ambas implementaciones
    assert result_mem["valid_orders"] == result_json["valid_orders"]
    assert result_mem["total_revenue"] == pytest.approx(result_json["total_revenue"], rel=1e-2)
    assert result_mem["orders_by_status"] == result_json["orders_by_status"]


def test_lsp_json_repo_persiste_en_disco(valid_orders, tmp_path):
    """JsonFileOrderRepository escribe el resumen en disco correctamente."""
    orders_file = tmp_path / "orders.json"
    summary_file = tmp_path / "output" / "summary.json"
    orders_file.write_text(json.dumps(valid_orders, ensure_ascii=False), encoding="utf-8")

    repo = JsonFileOrderRepository(
        orders_path=orders_file,
        summary_path=summary_file,
    )
    OrderService(repository=repo).process_orders()

    assert summary_file.exists()
    saved = json.loads(summary_file.read_text(encoding="utf-8"))
    assert saved["valid_orders"] == 2


def test_lsp_memory_repo_guarda_resumen_en_memoria(service, memory_repo):
    """InMemoryOrderRepository almacena el resumen en memoria."""
    service.process_orders()
    assert memory_repo.last_summary is not None
    assert memory_repo.last_summary["valid_orders"] == 2


# ---------------------------------------------------------------------------
# SRP — OrderValidator solo valida, no tiene E/S
# ---------------------------------------------------------------------------


def test_srp_validator_acepta_orden_valida():
    validator = OrderValidator()
    ok, msg = validator.validate(VALID_ORDER)
    assert ok is True
    assert msg == ""


def test_srp_validator_rechaza_sin_email():
    validator = OrderValidator()
    ok, msg = validator.validate(INVALID_ORDER_NO_EMAIL)
    assert ok is False
    assert "email" in msg.lower()


def test_srp_validator_rechaza_nombre_vacio():
    validator = OrderValidator()
    ok, msg = validator.validate(INVALID_ORDER_EMPTY_NAME)
    assert ok is False
    assert "customer_name" in msg.lower()


@pytest.mark.parametrize(
    "bad_order, expected_error",
    [
        (
            {
                "order_id": "X",
                "customer_name": "Y",
                "email": "bad",
                "status": "pending",
                "items": [{"product_name": "P", "quantity": 1, "price": 1.0}],
            },
            "email inválido",
        ),
        (
            {
                "order_id": "X",
                "customer_name": "Y",
                "email": "a@b.com",
                "status": "inventado",
                "items": [{"product_name": "P", "quantity": 1, "price": 1.0}],
            },
            "status inválido",
        ),
        (
            {
                "order_id": "X",
                "customer_name": "Y",
                "email": "a@b.com",
                "status": "pending",
                "items": [],
            },
            "al menos un item",
        ),
        (
            {
                "order_id": "X",
                "customer_name": "Y",
                "email": "a@b.com",
                "status": "pending",
                "items": [{"product_name": "P", "quantity": -1, "price": 1.0}],
            },
            "quantity",
        ),
    ],
)
def test_srp_validator_detecta_errores_especificos(bad_order: dict, expected_error: str) -> None:
    """OrderValidator detecta cada tipo de error de forma independiente."""
    validator = OrderValidator()
    ok, msg = validator.validate(bad_order)
    assert ok is False
    assert expected_error.lower() in msg.lower()


# ---------------------------------------------------------------------------
# OCP — añadir un validador personalizado sin modificar OrderService
# ---------------------------------------------------------------------------


class StrictEmailValidator:
    """
    Validador personalizado que rechaza emails de dominios de prueba.
    OCP: se añade nueva lógica SIN modificar OrderService ni OrderValidator.
    """

    def validate(self, order: dict[str, Any]) -> tuple[bool, str]:
        base = OrderValidator()
        ok, msg = base.validate(order)
        if not ok:
            return ok, msg

        email: str = order.get("email", "")
        if email.endswith("@test.com") or email.endswith("@example.com"):
            return False, f"Dominio de prueba no permitido: {email}"

        return True, ""


def test_ocp_validador_personalizado_sin_modificar_service(memory_repo):
    """
    OCP: OrderService acepta un validador personalizado por inyección,
    sin modificar ninguna clase existente.
    """
    strict = StrictEmailValidator()
    service = OrderService(repository=memory_repo, validator=strict)

    # Ambas órdenes tienen @example.com → deben ser rechazadas
    result = service.process_orders()

    assert result["valid_orders"] == 0
    assert result["invalid_orders"] == 2


# ---------------------------------------------------------------------------
# Integración: flujo completo con InMemory
# ---------------------------------------------------------------------------


def test_integracion_flujo_completo(mixed_orders):
    """
    Prueba el flujo completo: cargar → validar → procesar → guardar resumen.
    4 órdenes: 2 válidas, 2 inválidas.
    """
    repo = InMemoryOrderRepository(orders=mixed_orders)
    service = OrderService(repository=repo)
    result = service.process_orders(skip_invalid=True)

    assert result["valid_orders"] == 2
    assert result["invalid_orders"] == 2
    assert result["total_revenue"] > 0
    assert repo.last_summary is not None


def test_integracion_skip_false_lanza_excepcion(mixed_orders):
    """Con skip_invalid=False, la primera orden inválida lanza ValueError."""
    repo = InMemoryOrderRepository(orders=mixed_orders)
    service = OrderService(repository=repo)

    with pytest.raises(ValueError, match="inválida"):
        service.process_orders(skip_invalid=False)
