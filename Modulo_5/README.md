# Módulo 5 - Tipado estático y calidad

## Objetivo

Añadir anotaciones de tipos, configuración de mypy y verificar el estilo con Black, isort y Ruff.

## Qué se realizó

- Se anotaron las entidades, servicios, utilidades y funciones principales.
- Se configuraron mypy, Ruff, isort y Black en `pyproject.toml`.
- Se activaron reglas de calidad mediante pre-commit.
- Se mantuvieron las demostraciones y modelos de los módulos anteriores.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_5
poetry install
poetry run mypy src/
poetry run ruff check src/ scripts/ tests/
poetry run black --check src/ scripts/ tests/
poetry run isort --check-only src/ scripts/ tests/
```

Los comandos pueden combinarse antes de una entrega:

```cmd
poetry run pre-commit run --all-files
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`.
