"""
Validador de órdenes - Módulo 12: SOLID
SRP: esta clase tiene una sola razón de cambiar — las reglas de validación.
Extraído de OrderProcessor (Módulo 2) sin modificar la lógica original.
"""

import re
from typing import Any

from order_management.domain.value_objects import OrderStatus


class OrderValidator:
    """
    Valida órdenes de compra contra las reglas de negocio.

    SRP: solo valida — no carga archivos, no calcula totales,
         no acumula estadísticas.

    Cumple OrderValidatorPort (duck typing estructural).
    """

    # Statuses válidos tomados del dominio existente
    VALID_STATUSES: frozenset[str] = frozenset(s.value for s in OrderStatus)

    def validate(self, order: dict[str, Any]) -> tuple[bool, str]:
        """
        Valida una orden individual.

        Args:
            order: Diccionario con datos de la orden

        Returns:
            Tupla (es_válida, mensaje_error)
        """
        # 1. Campos requeridos
        required = {"order_id", "customer_name", "email", "items", "status"}
        missing = required - order.keys()
        if missing:
            return False, f"Faltan campos requeridos: {missing}"

        # 2. order_id no vacío
        if not str(order["order_id"]).strip():
            return False, "order_id no puede estar vacío"

        # 3. customer_name no vacío
        if not str(order["customer_name"]).strip():
            return False, "customer_name no puede estar vacío"

        # 4. email válido
        email = str(order.get("email", "")).strip()
        if not email:
            return False, "email no puede estar vacío"
        if not self._valid_email(email):
            return False, f"email inválido: {email}"

        # 5. status válido
        if order["status"] not in self.VALID_STATUSES:
            return False, (
                f"status inválido: '{order['status']}'. "
                f"Válidos: {self.VALID_STATUSES}"
            )

        # 6. items
        items = order["items"]
        if not isinstance(items, list) or not items:
            return False, "La orden debe tener al menos un item"

        for idx, item in enumerate(items):
            ok, msg = self._validate_item(idx, item)
            if not ok:
                return False, msg

        return True, ""

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_item(idx: int, item: Any) -> tuple[bool, str]:
        """Valida un item individual de la orden."""
        if not isinstance(item, dict):
            return False, f"Item {idx} debe ser un diccionario"

        required = {"product_name", "quantity", "price"}
        missing = required - item.keys()
        if missing:
            return False, f"Item {idx} falta campos: {missing}"

        if not str(item["product_name"]).strip():
            return False, f"Item {idx}: product_name no puede estar vacío"

        if not isinstance(item["quantity"], int | float) or item["quantity"] <= 0:
            return False, f"Item {idx}: quantity inválida"

        if not isinstance(item["price"], int | float) or item["price"] < 0:
            return False, f"Item {idx}: price inválido"

        return True, ""

    @staticmethod
    def _valid_email(email: str) -> bool:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
