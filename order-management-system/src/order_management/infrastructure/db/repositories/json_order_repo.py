"""
Repositorio JSON - Módulo 12: SOLID
Implementación de OrderRepositoryPort que lee/escribe en disco.

OCP: añadir este repositorio no modifica OrderService ni el dominio.
SRP: solo gestiona la E/S con archivos JSON.
"""

import json
from pathlib import Path
from typing import Any

from order_management.domain.ports import OrderRepositoryPort


class JsonFileOrderRepository:
    """
    Implementación de OrderRepositoryPort que usa el sistema de archivos.

    Corresponde a la lógica de E/S que antes vivía en OrderProcessor
    (Módulo 2). Al extraerla aquí:
      - OrderService queda limpio de E/S
      - Es fácil sustituirla por otra implementación (LSP)
    """

    def __init__(
        self,
        orders_path: Path | str,
        summary_path: Path | str,
    ) -> None:
        self._orders_path = Path(orders_path)
        self._summary_path = Path(summary_path)

    # ------------------------------------------------------------------
    # OrderRepositoryPort
    # ------------------------------------------------------------------

    def load_orders(self) -> list[dict[str, Any]]:
        """Lee órdenes desde el archivo JSON configurado."""
        if not self._orders_path.exists():
            raise FileNotFoundError(
                f"Archivo de órdenes no encontrado: {self._orders_path}"
            )
        if self._orders_path.suffix.lower() != ".json":
            raise ValueError(
                f"El archivo debe ser .json, recibido: {self._orders_path.suffix}"
            )

        data = json.loads(self._orders_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("El JSON debe contener una lista de órdenes")

        return data  # type: ignore[return-value]

    def save_summary(self, summary: dict[str, Any]) -> None:
        """Escribe el resumen en el archivo JSON configurado."""
        self._summary_path.parent.mkdir(parents=True, exist_ok=True)
        self._summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# Verificación estática: JsonFileOrderRepository cumple el Protocol
def _assert_protocol_compliance() -> None:
    """Falla en import si JsonFileOrderRepository no cumple OrderRepositoryPort."""
    _: OrderRepositoryPort = JsonFileOrderRepository(
        orders_path="dummy.json",
        summary_path="dummy_out.json",
    )
