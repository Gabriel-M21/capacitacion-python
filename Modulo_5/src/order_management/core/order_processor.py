"""
Procesador de órdenes - Módulo 2: Fundamentos del lenguaje
Demuestra: tipos básicos, colecciones, control de flujo, pattern matching, excepciones
"""

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any


class OrderStatus(Enum):
    """Estados posibles de una orden"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class OrderProcessor:
    """Procesador de órdenes con manejo robusto de errores"""

    def __init__(self) -> None:
        """Inicializa el procesador con estadísticas vacías"""
        self.total_orders: int = 0
        self.total_revenue: float = 0.0
        self.orders_by_status: dict[str, int] = {}
        self.unique_customers: set[str] = set()
        self.processed_orders: list[dict[str, Any]] = []

    def load_orders_from_json(self, filepath: Path | str) -> list[dict[str, Any]]:
        """
        Carga órdenes desde archivo JSON con manejo robusto de errores.

        Args:
            filepath: Ruta al archivo JSON

        Returns:
            Lista de órdenes válidas

        Raises:
            FileNotFoundError: Si el archivo no existe
            json.JSONDecodeError: Si el JSON es inválido
            ValueError: Si el contenido no es una lista
        """
        # Convertir a Path si es string
        file_path = Path(filepath) if isinstance(filepath, str) else filepath

        # Validar que el archivo existe
        if not file_path.exists():
            raise FileNotFoundError(f"El archivo {file_path} no existe")

        # Validar extensión
        if file_path.suffix.lower() != ".json":
            raise ValueError(f"El archivo debe ser .json, recibido: {file_path.suffix}")

        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)

            # Validar que sea una lista
            if not isinstance(data, list):
                raise ValueError("El JSON debe contener una lista de órdenes")

            return data

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Error al parsear JSON: {e.msg}", e.doc, e.pos) from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Error de codificación en el archivo: {e}") from e

    def validate_order(self, order: dict[str, Any]) -> tuple[bool, str]:
        """
        Valida que una orden tenga los campos requeridos.

        Args:
            order: Diccionario con datos de la orden

        Returns:
            Tupla (es_válida, mensaje_error)
        """
        required_fields = {"order_id", "customer_name", "email", "items", "status"}
        missing_fields = required_fields - order.keys()

        if missing_fields:
            return False, f"Faltan campos requeridos: {missing_fields}"

        # Validar order_id no vacío
        if not order["order_id"] or not str(order["order_id"]).strip():
            return False, "order_id no puede estar vacío"

        # Validar customer_name no vacío
        if not order["customer_name"] or not str(order["customer_name"]).strip():
            return False, "customer_name no puede estar vacío"

        # Validar email
        email = order.get("email", "")
        if not email or not str(email).strip():
            return False, "email no puede estar vacío"
        if not self.validate_email(email):
            return False, f"email inválido: {email}"

        # Validar status contra enum
        valid_statuses = {s.value for s in OrderStatus}
        if order["status"] not in valid_statuses:
            return False, f"status inválido: {order['status']}. Válidos: {valid_statuses}"

        # Validar items
        if not isinstance(order["items"], list) or len(order["items"]) == 0:
            return False, "La orden debe tener al menos un item"

        # Validar cada item
        for idx, item in enumerate(order["items"]):
            if not isinstance(item, dict):
                return False, f"Item {idx} debe ser un diccionario"

            required_item_fields = {"product_name", "quantity", "price"}
            missing_item_fields = required_item_fields - item.keys()

            if missing_item_fields:
                return False, f"Item {idx} falta campos: {missing_item_fields}"

            # Validar product_name no vacío
            if not item["product_name"] or not str(item["product_name"]).strip():
                return False, f"Item {idx}: product_name no puede estar vacío"

            # Validar tipos
            if not isinstance(item["quantity"], int | float) or item["quantity"] <= 0:
                return False, f"Item {idx} tiene cantidad inválida"

            if not isinstance(item["price"], int | float) or item["price"] < 0:
                return False, f"Item {idx} tiene precio inválido"

        return True, ""

    def calculate_order_total(self, items: list[dict[str, Any]]) -> float:
        """
        Calcula el total de una orden.

        Args:
            items: Lista de items con 'quantity' y 'price'

        Returns:
            Total calculado
        """
        total = 0.0
        for item in items:
            quantity = item.get("quantity", 0)
            price = item.get("price", 0.0)
            total += quantity * price

        return round(total, 2)

    def filter_orders_by_status(
        self, orders: list[dict[str, Any]], status: str
    ) -> list[dict[str, Any]]:
        """
        Filtra órdenes por estado usando comprehension.

        Args:
            orders: Lista de órdenes
            status: Estado a filtrar

        Returns:
            Lista de órdenes filtradas
        """
        return [order for order in orders if order.get("status") == status]

    def filter_orders_by_min_total(
        self, orders: list[dict[str, Any]], min_total: float
    ) -> list[dict[str, Any]]:
        """
        Filtra órdenes con total mayor o igual al mínimo.

        Args:
            orders: Lista de órdenes
            min_total: Total mínimo

        Returns:
            Lista de órdenes filtradas
        """
        filtered = []
        for order in orders:
            total = self.calculate_order_total(order["items"])
            if total >= min_total:
                order["total"] = total
                filtered.append(order)

        return filtered

    def categorize_order_by_total(self, total: float) -> str:
        """
        Categoriza una orden por su total usando pattern matching (Python 3.10+).

        Args:
            total: Total de la orden

        Returns:
            Categoría de la orden
        """
        match total:
            case t if t < 0:
                return "INVALID"
            case t if t == 0:
                return "EMPTY"
            case t if 0 < t < 50:
                return "SMALL"
            case t if 50 <= t < 200:
                return "MEDIUM"
            case t if 200 <= t < 1500:
                return "LARGE"
            case _:
                return "ENTERPRISE"

    def validate_email(self, email: str) -> bool:
        """
        Valida formato de email usando expresión regular.

        Args:
            email: Email a validar

        Returns:
            True si es válido
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def process_orders(
        self, orders: list[dict[str, Any]], skip_invalid: bool = True
    ) -> dict[str, Any]:
        """
        Procesa una lista de órdenes y genera estadísticas.

        Args:
            orders: Lista de órdenes a procesar
            skip_invalid: Si True, omite órdenes inválidas; si False, lanza excepción

        Returns:
            Diccionario con estadísticas y órdenes procesadas

        Raises:
            ValueError: Si skip_invalid es False y hay órdenes inválidas
        """
        valid_orders = []
        invalid_orders = []

        for idx, order in enumerate(orders):
            is_valid, error_msg = self.validate_order(order)

            if not is_valid:
                invalid_orders.append({"index": idx, "error": error_msg, "order": order})
                if not skip_invalid:
                    raise ValueError(f"Orden {idx} inválida: {error_msg}")
                continue

            # Calcular total
            total = self.calculate_order_total(order["items"])
            order["total"] = total
            order["category"] = self.categorize_order_by_total(total)

            # Actualizar estadísticas
            self.total_orders += 1
            self.total_revenue += total
            self.unique_customers.add(order["customer_name"])

            status = order["status"]
            self.orders_by_status[status] = self.orders_by_status.get(status, 0) + 1

            valid_orders.append(order)

        self.processed_orders = valid_orders

        return {
            "total_orders": self.total_orders,
            "valid_orders": len(valid_orders),
            "invalid_orders": len(invalid_orders),
            "total_revenue": round(self.total_revenue, 2),
            "average_order_value": (
                round(self.total_revenue / self.total_orders, 2) if self.total_orders > 0 else 0.0
            ),
            "unique_customers": len(self.unique_customers),
            "orders_by_status": self.orders_by_status,
            "invalid_details": invalid_orders,
        }

    def get_top_customers(self, top_n: int = 5) -> list[tuple[str, float]]:
        """
        Obtiene los top N clientes por revenue.

        Args:
            top_n: Número de clientes a retornar

        Returns:
            Lista de tuplas (customer_name, total_spent) ordenadas descendente
        """
        customer_totals: dict[str, float] = {}

        for order in self.processed_orders:
            customer = order["customer_name"]
            total = order["total"]
            customer_totals[customer] = customer_totals.get(customer, 0.0) + total

        # Convertir a lista de tuplas y ordenar
        sorted_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)

        return sorted_customers[:top_n]

    def export_summary_to_json(self, filepath: Path | str, stats: dict[str, Any]) -> None:
        """
        Exporta estadísticas a archivo JSON.

        Args:
            filepath: Ruta del archivo de salida
            stats: Diccionario con estadísticas

        Raises:
            OSError: Si hay error al escribir el archivo
        """
        file_path = Path(filepath) if isinstance(filepath, str) else filepath

        try:
            # Crear directorio si no existe
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(stats, file, indent=2, ensure_ascii=False)

        except OSError as e:
            raise OSError(f"Error al escribir archivo {file_path}: {e}") from e
