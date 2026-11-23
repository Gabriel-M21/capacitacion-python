# Módulo 4 - Objetos y modelos de datos

## Objetivo

Modelar órdenes mediante clases, dataclasses, Pydantic y objetos de valor, incluyendo validación y serialización.

## Qué se realizó

- Entidades de dominio en `src/order_management/domain/entities.py`.
- Objetos de valor en `src/order_management/domain/value_objects.py`.
- Modelos Pydantic de entrada y salida.
- Conversión entre modelos y entidades mediante mappers.
- Demostración ejecutable en `scripts/demo_module_4.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_4
poetry install
poetry run python scripts/demo_module_4.py
```

Validar tipos:

```cmd
poetry run mypy src/
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`.
