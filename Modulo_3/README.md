# Módulo 3 - Funciones y programación Pythonica

## Objetivo

Practicar funciones claras, decoradores, generadores, iteradores, comprensiones y context managers aplicados a pedidos.

## Qué se realizó

- Decorador de reintentos con backoff en `src/order_management/utils/decorators.py`.
- Generadores para procesar colecciones por lotes.
- Context managers para recursos y medición de tiempo.
- Script demostrativo `scripts/demo_module_3.py`.
- Ejemplo de procesamiento incremental de órdenes.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_3
poetry install
poetry run python scripts/demo_module_3.py
```

Comprobación de estilo:

```cmd
poetry run ruff check src/ scripts/ tests/
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`.
