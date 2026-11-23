# Módulo 1 - Entorno y herramientas

## Objetivo

Preparar el entorno de desarrollo de `order-management-system` con Python, Poetry y VS Code, y configurar las herramientas básicas de calidad utilizadas durante la capacitación.

## Qué se realizó

- Se creó el proyecto con una estructura compatible con `src/`.
- Se configuró Poetry mediante `pyproject.toml` y `poetry.lock`.
- Se dejó disponible el paquete `order_management`.
- Se añadió una utilidad inicial en `src/order_management/utils.py`.
- Se configuraron Black, isort, Ruff, mypy y pre-commit.

## Estructura principal

```text
Modulo_1/
├── src/order_management/utils.py
├── tests/
├── pyproject.toml
├── poetry.lock
├── .pre-commit-config.yaml
└── README.md
```

## Ejecución

Abre CMD en la raíz del repositorio. Con Python 3.12 y Poetry instalados:

```cmd
cd /d Modulo_1
poetry install
poetry run python -c "import order_management.utils as utils; print(utils.__file__)"
```

Instalar y ejecutar los hooks antes de entregar:

```cmd
poetry run pre-commit install
poetry run pre-commit run --all-files
```

Herramientas de calidad:

```cmd
poetry run black --check src/ tests/
poetry run isort --check-only src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`; por eso no se
incluye un comando pytest ejecutable aquí.
