"""
Decoradores útiles para el procesamiento de órdenes - Módulo 3
Demuestra: decoradores, closures, *args/**kwargs
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorador que reintenta una función con backoff exponencial.

    Args:
        max_attempts: Número máximo de intentos
        initial_delay: Delay inicial en segundos
        backoff_factor: Factor multiplicador del delay
        exceptions: Tupla de excepciones a capturar

    Returns:
        Función decorada con lógica de reintentos

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=0.5)
        def load_external_orders():
            # Código que puede fallar
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Intento {attempt}/{max_attempts} de {func.__name__}")
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(f"{func.__name__} exitoso en intento {attempt}")
                    return result

                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} falló después de {max_attempts} intentos: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} falló (intento {attempt}/{max_attempts}): {e}. "
                        f"Reintentando en {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} falló sin excepción específica")

        return wrapper

    return decorator


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorador que mide el tiempo de ejecución de una función.

    Args:
        func: Función a decorar

    Returns:
        Función decorada que registra el tiempo

    Example:
        @measure_time
        def process_large_batch():
            # Código a medir
            pass
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time

        logger.info(f"{func.__name__} ejecutado en {elapsed_time:.4f} segundos")
        return result

    return wrapper


def validate_order_data(**validators: Callable[[Any], bool]) -> Callable:
    """
    Decorador que valida argumentos de funciones de órdenes.

    Args:
        **validators: Diccionario {nombre_arg: función_validadora}

    Returns:
        Decorador que valida los argumentos

    Example:
        @validate_order_data(
            total=lambda x: x > 0,
            customer_name=lambda x: isinstance(x, str) and len(x) > 0
        )
        def create_order(customer_name: str, total: float):
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            import inspect

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Validación falló para '{param_name}': {value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_order_operation(operation: str) -> Callable:
    """
    Decorador que registra operaciones sobre órdenes.

    Args:
        operation: Nombre de la operación

    Returns:
        Decorador que registra la operación

    Example:
        @log_order_operation("CREATE")
        def create_order(order_data):
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger.info(f"[{operation}] Iniciando {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"[{operation}] {func.__name__} completado exitosamente")
                return result
            except Exception as e:
                logger.error(f"[{operation}] {func.__name__} falló: {e}")
                raise

        return wrapper

    return decorator


# Closures útiles para órdenes
def create_discount_calculator(discount_percentage: float) -> Callable[[float], float]:
    """
    Crea una función que aplica un descuento específico (closure).

    Args:
        discount_percentage: Porcentaje de descuento (0-100)

    Returns:
        Función que aplica el descuento

    Example:
        black_friday = create_discount_calculator(50)
        final_price = black_friday(100)  # 50.0
    """
    if not 0 <= discount_percentage <= 100:
        raise ValueError("Descuento debe estar entre 0 y 100")

    def apply_discount(price: float) -> float:
        return price * (1 - discount_percentage / 100)

    return apply_discount


def create_order_filter(
    **criteria: Any,
) -> Callable[[dict[str, Any]], bool]:
    """
    Crea una función filtro para órdenes (closure).

    Args:
        **criteria: Criterios de filtrado

    Returns:
        Función que evalúa si una orden cumple los criterios

    Example:
        high_value_filter = create_order_filter(min_total=100, status="confirmed")
        matching_orders = [o for o in orders if high_value_filter(o)]
    """

    def filter_func(order: dict[str, Any]) -> bool:
        for key, expected_value in criteria.items():
            if key.startswith("min_"):
                actual_key = key[4:]
                if order.get(actual_key, 0) < expected_value:
                    return False
            elif key.startswith("max_"):
                actual_key = key[4:]
                if order.get(actual_key, float("inf")) > expected_value:
                    return False
            else:
                if order.get(key) != expected_value:
                    return False
        return True

    return filter_func
