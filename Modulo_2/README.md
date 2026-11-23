# Módulo 2 - Fundamentos del lenguaje

## Objetivo

Aplicar sintaxis básica de Python, colecciones, control de flujo, excepciones y pattern matching al procesamiento de pedidos.

## Qué se realizó

- Se creó `OrderProcessor` en `src/order_management/core/order_processor.py`.
- Se incorporó procesamiento de datos y validación de entradas.
- Se añadió el script `scripts/run_order_processor.py` para ejecutar el ejemplo desde la terminal.
- Se reutilizaron utilidades para demostrar el manejo de datos.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_2
poetry install
poetry run python scripts/run_order_processor.py
```

Para comprobar la calidad del código:

```cmd
poetry run ruff check src/ scripts/ tests/
poetry run mypy src/
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`.
