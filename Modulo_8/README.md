# Módulo 8 - Acceso a datos y ORM

## Objetivo

Modelar pedidos, usuarios y partidas con SQLAlchemy, ejecutar operaciones CRUD y administrar migraciones con Alembic.

## Qué se realizó

- Modelos SQLAlchemy en `src/order_management/infrastructure/db/models.py`.
- Sesión y configuración de base en `src/order_management/infrastructure/db/session.py`.
- Repositorio de órdenes.
- Migraciones Alembic en `alembic/`.
- Demostración CRUD en `scripts/demo_module_8.py`.

## Ejecución

Abre CMD en la raíz del repositorio. SQLite es local; no necesitas iniciar un
contenedor ni un servidor de base de datos.

```cmd
cd /d Modulo_8
poetry install
poetry run alembic upgrade head
poetry run python scripts/demo_module_8.py
```

Operaciones útiles:

```cmd
poetry run alembic history
poetry run alembic current
```

La base de datos del laboratorio es SQLite local; no requiere Docker ni un servidor
de base de datos. Este módulo todavía no contiene archivos de pruebas `test_*.py`.
