# Módulo 10 - Pruebas y TDD

## Objetivo

Diseñar pruebas fiables con pytest, fixtures, parametrización, mocking, Hypothesis y cobertura.

## Qué se realizó

- Pruebas de API y dominio.
- Fixtures compartidos en `tests/conftest.py`.
- Tests parametrizados del descuento por volumen.
- Tests de propiedades con Hypothesis.
- Integración de cobertura mediante pytest-cov.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_10
poetry install
poetry run pytest -v
```

Ejecutar sólo las pruebas de precios:

```cmd
poetry run pytest -q tests/test_pricing.py
```
