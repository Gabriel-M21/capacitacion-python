# Módulo 15 - Arquitectura Hexagonal

## Objetivo

Separar dominio, aplicación e infraestructura mediante puertos y adaptadores.

## Qué se realizó

- Puerto de repositorio y puerto de notificación.
- Caso de uso `CreateOrderUseCase`.
- DTO de creación de órdenes.
- Adaptadores en memoria, JSON, HTTP y SQLAlchemy.
- Wiring de infraestructura desde la aplicación.
- Pruebas hexagonales en `tests/test_hexagonal.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_15
poetry install
poetry run python scripts/demo_module_15.py
poetry run pytest -q tests/test_hexagonal.py
```

Ejecución completa de pruebas:

```cmd
poetry run pytest -q
```

La demo y las pruebas usan adaptadores locales/en memoria; no hace falta levantar
FastAPI, Docker ni Smocker.
