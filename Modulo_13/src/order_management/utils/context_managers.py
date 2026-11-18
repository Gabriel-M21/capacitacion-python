"""
Context managers para gestión de recursos - Módulo 3
Demuestra: context managers, with statement, __enter__/__exit__
"""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Timer:
    """
    Context manager para medir tiempo de procesamiento de órdenes.

    Example:
        with Timer("Procesamiento de órdenes"):
            process_orders(orders)
        # Output: Procesamiento de órdenes completado en 2.3456 segundos
    """

    def __init__(self, operation_name: str = "Operación") -> None:
        """
        Inicializa el timer.

        Args:
            operation_name: Nombre de la operación a medir
        """
        self.operation_name = operation_name
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0

    def __enter__(self) -> "Timer":
        """
        Entra al contexto y comienza a medir tiempo.

        Returns:
            Instancia del Timer
        """
        logger.info(f"{self.operation_name} iniciado...")
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Sale del contexto y registra el tiempo transcurrido.

        Args:
            exc_type: Tipo de excepción (si ocurrió)
            exc_val: Valor de la excepción
            exc_tb: Traceback de la excepción

        Returns:
            False para propagar excepciones
        """
        self.elapsed_time = time.perf_counter() - self.start_time

        if exc_type is not None:
            logger.error(
                f"{self.operation_name} falló después de {self.elapsed_time:.4f}s: {exc_val}"
            )
        else:
            logger.info(f"{self.operation_name} completado en {self.elapsed_time:.4f} segundos")


class OrderProcessingContext:
    """
    Context manager para procesamiento de órdenes con rollback.

    Example:
        with OrderProcessingContext(orders) as ctx:
            ctx.process_batch(batch1)
            ctx.process_batch(batch2)
        # Si hay error, se registra para auditoría
    """

    def __init__(self, orders: list[dict[str, Any]]) -> None:
        """
        Inicializa el contexto.

        Args:
            orders: Lista de órdenes a procesar
        """
        self.orders = orders
        self.processed: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.start_time: float = 0.0

    def __enter__(self) -> "OrderProcessingContext":
        """
        Entra al contexto de procesamiento.

        Returns:
            Instancia del contexto
        """
        logger.info(f"Iniciando procesamiento de {len(self.orders)} órdenes")
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Sale del contexto y genera reporte.

        Args:
            exc_type: Tipo de excepción
            exc_val: Valor de la excepción
            exc_tb: Traceback

        Returns:
            False para propagar excepciones
        """
        elapsed = time.perf_counter() - self.start_time

        if exc_type is not None:
            logger.error(f"Error en procesamiento: {exc_val}")
            logger.info(f"Procesadas: {len(self.processed)}, Fallidas: {len(self.failed)}")
        else:
            logger.info(
                f"Procesamiento completado en {elapsed:.4f}s: "
                f"{len(self.processed)} exitosas, {len(self.failed)} fallidas"
            )

    def process_order(self, order: dict[str, Any]) -> bool:
        """
        Procesa una orden individual.

        Args:
            order: Orden a procesar

        Returns:
            True si fue exitoso
        """
        try:
            # Aquí iría la lógica real de procesamiento
            self.processed.append(order)
            return True
        except Exception as e:
            logger.warning(f"Error procesando orden {order.get('order_id')}: {e}")
            self.failed.append(order)
            return False


@contextmanager
def order_file_handler(
    filepath: Path | str, create_backup: bool = True
) -> Generator[Path, None, None]:
    """
    Context manager para manejo seguro de archivos de órdenes.

    Args:
        filepath: Ruta del archivo
        create_backup: Si True, crea backup antes de escribir

    Yields:
        Path del archivo

    Example:
        with order_file_handler('orders.json', backup=True) as path:
            # Trabajar con el archivo
            save_orders(path, orders)
        # Backup se elimina si todo fue exitoso
    """
    file_path = Path(filepath) if isinstance(filepath, str) else filepath
    backup_path = None

    try:
        # Crear backup si existe
        if create_backup and file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            import shutil

            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup creado: {backup_path}")

        yield file_path

    except Exception:
        # Si hay error y existe backup, restaurar
        if backup_path and backup_path.exists():
            import shutil

            logger.warning(f"Restaurando backup desde {backup_path}")
            shutil.copy2(backup_path, file_path)
        raise

    finally:
        # Limpiar backup si todo salió bien
        if backup_path and backup_path.exists():
            backup_path.unlink()
            logger.debug("Backup eliminado")


@contextmanager
def batch_processing_context(
    batch_size: int,
) -> Generator[dict[str, Any], None, None]:
    """
    Context manager para procesamiento por lotes con estadísticas.

    Args:
        batch_size: Tamaño del lote

    Yields:
        Diccionario con estadísticas del lote

    Example:
        with batch_processing_context(batch_size=100) as stats:
            for order in batch:
                stats['processed'] += 1
        # Muestra resumen al finalizar
    """
    stats = {"batch_size": batch_size, "processed": 0, "errors": 0}
    start_time = time.perf_counter()

    try:
        logger.info(f"Iniciando procesamiento de lote (tamaño: {batch_size})")
        yield stats

    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(
            f"Lote completado en {elapsed:.4f}s: "
            f"{stats['processed']} procesadas, {stats['errors']} errores"
        )


class OrderTransaction:
    """
    Context manager para transacciones de órdenes (simulado).

    Example:
        with OrderTransaction() as tx:
            tx.create_order(order1)
            tx.update_inventory(items)
        # Auto-commit si no hay errores, rollback automático si falla
    """

    def __init__(self) -> None:
        """Inicializa la transacción."""
        self.in_transaction = False
        self.operations: list[str] = []

    def __enter__(self) -> "OrderTransaction":
        """
        Inicia la transacción.

        Returns:
            Instancia de la transacción
        """
        logger.info("Iniciando transacción de orden")
        self.in_transaction = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Finaliza la transacción.

        Args:
            exc_type: Tipo de excepción
            exc_val: Valor de la excepción
            exc_tb: Traceback

        Returns:
            False para propagar excepciones
        """
        if exc_type is not None:
            logger.warning(f"Rollback de transacción: {exc_val}")
            logger.debug(f"Operaciones en rollback: {self.operations}")
        else:
            logger.info("Commit de transacción")
            logger.debug(f"Operaciones confirmadas: {self.operations}")

        self.in_transaction = False

    def execute(self, operation: str) -> None:
        """
        Ejecuta una operación en la transacción.

        Args:
            operation: Descripción de la operación
        """
        if not self.in_transaction:
            raise RuntimeError("No hay transacción activa")
        self.operations.append(operation)
        logger.debug(f"Operación registrada: {operation}")
