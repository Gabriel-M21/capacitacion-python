# Módulo 12 - Principios SOLID

## Objetivo

Reducir acoplamiento y mejorar la testabilidad aplicando SRP, OCP, LSP, ISP y DIP.

## Qué se realizó

- Puertos definidos con `Protocol` en `src/order_management/domain/ports.py`.
- Servicios separados: validación y operación de órdenes.
- Repositorios alternables en memoria y JSON.
- Implementaciones reemplazables sin modificar el dominio.
- Pruebas SOLID en `tests/test_solid.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_12
poetry install
poetry run python scripts/demo_module_12.py
poetry run pytest -q tests/test_solid.py
```

Ejecutar todas las comprobaciones:

```cmd
poetry run pytest -q
poetry run mypy src/
```
