"""
Servicio de órdenes - Módulo 12: SOLID
Orquesta la lógica de negocio sin conocer detalles de infraestructura.

SRP: solo orquesta — no lee archivos, no persiste directamente.
DIP: depende de puertos (Protocol), no de implementaciones concretas.
OCP: añadir una nueva fuente de datos no requiere modificar este servicio.
"""

from decimal import Decimal
from typing import Any

from order_management.domain.ports import OrderRepositoryPort, OrderValidatorPort
from order_management.services.order_validator import OrderValidator


class OrderService:
    """
    Servicio de dominio para procesar órdenes.

    DIP: recibe sus dependencias por constructor (inyección de dependencias).
         Depende de OrderRepositoryPort y OrderValidatorPort — nunca de
         JsonFileOrderRepository o InMemoryOrderRepository directamente.

    SRP: su única razón de cambiar es la lógica de negocio de procesamiento.
    """

    def __init__(
        self,
        repository: OrderRepositoryPort,
        validator: OrderValidatorPort | None = None,
    ) -> None:
        """
        Args:
            repository: Implementación del puerto de datos
            validator:  Implementación del puerto de validación.
                        Si no se provee, usa OrderValidator por defecto.
        """
        self._repo = repository
        self._validator = validator or OrderValidator()

    # ------------------------------------------------------------------
    # Operaciones principales
    # ------------------------------------------------------------------

    def process_orders(self, skip_invalid: bool = True) -> dict[str, Any]:
        """
        Carga, valida y procesa todas las órdenes del repositorio.

        Args:
            skip_invalid: Si True omite órdenes inválidas;
                          si False lanza ValueError en la primera inválida.

        Returns:
            Diccionario con estadísticas del procesamiento.

        Raises:
            ValueError: Si skip_invalid=False y hay una orden inválida.
        """
        raw_orders = self._repo.load_orders()

        valid_orders: list[dict[str, Any]] = []
        invalid_orders: list[dict[str, Any]] = []
        total_revenue = Decimal("0")
        orders_by_status: dict[str, int] = {}
        unique_customers: set[str] = set()

        for idx, order in enumerate(raw_orders):
            is_valid, error_msg = self._validator.validate(order)

            if not is_valid:
                invalid_orders.append(
                    {
                        "index": idx,
                        "error": error_msg,
                        "order": order,
                    }
                )
                if not skip_invalid:
                    raise ValueError(f"Orden {idx} inválida: {error_msg}")
                continue

            total = self._calculate_total(order["items"])
            order = {**order, "total": total, "category": self._categorize(total)}

            total_revenue += Decimal(str(total))
            unique_customers.add(order["customer_name"])
            status = order["status"]
            orders_by_status[status] = orders_by_status.get(status, 0) + 1

            valid_orders.append(order)

        n_valid = len(valid_orders)
        summary: dict[str, Any] = {
            "total_orders": n_valid,
            "valid_orders": n_valid,
            "invalid_orders": len(invalid_orders),
            "total_revenue": float(round(total_revenue, 2)),
            "average_order_value": (float(round(total_revenue / n_valid, 2)) if n_valid else 0.0),
            "unique_customers": len(unique_customers),
            "orders_by_status": orders_by_status,
            "invalid_details": invalid_orders,
        }

        self._repo.save_summary(summary)
        return summary

    def get_top_customers(
        self,
        orders: list[dict[str, Any]],
        top_n: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Calcula los top N clientes por revenue.

        Args:
            orders: Órdenes ya procesadas (con campo 'total')
            top_n:  Cuántos clientes devolver

        Returns:
            Lista de (customer_name, total_gastado) ordenada descendente
        """
        totals: dict[str, float] = {}
        for order in orders:
            name = order.get("customer_name", "")
            total = float(order.get("total", 0))
            totals[name] = totals.get(name, 0.0) + total

        return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # ------------------------------------------------------------------
    # Privado — lógica pura sin E/S
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_total(items: list[dict[str, Any]]) -> float:
        total = sum(float(i.get("quantity", 0)) * float(i.get("price", 0.0)) for i in items)
        return round(total, 2)

    @staticmethod
    def _categorize(total: float) -> str:
        if total < 0:
            return "INVALID"
        if total == 0:
            return "EMPTY"
        if total < 50:
            return "SMALL"
        if total < 200:
            return "MEDIUM"
        if total < 1500:
            return "LARGE"
        return "ENTERPRISE"
