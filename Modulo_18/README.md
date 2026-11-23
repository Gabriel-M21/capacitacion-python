# Módulo 18 - CLI y automatización

## Objetivo

Proporcionar una interfaz de línea de comandos para autenticar usuarios y gestionar órdenes mediante la API.

## Qué se realizó

- CLI construida con Typer.
- Comandos de autenticación en `src/order_management/cli/auth.py`.
- Comandos de órdenes en `src/order_management/cli/orders.py`.
- Configuración por variables de entorno.
- Entrada instalable `orders-cli` configurada en `pyproject.toml`.

## Ejecución

Abre CMD en la raíz del repositorio e inicia primero la API:

```cmd
cd /d Modulo_18
poetry install
poetry run uvicorn order_management.api.main:app --reload --port 8001
```

La API crea las tablas SQLite y los usuarios de prueba al arrancar. En otra
ventana CMD abierta también en la raíz del repositorio, configura esa URL, inicia
sesión y crea una orden de prueba:

```cmd
cd /d Modulo_18
set ORDERS_API_URL=http://localhost:8001
poetry run orders-cli --help
poetry run orders-cli info
poetry run orders-cli auth login
```

Cuando pregunte, usa `admin@example.com` y `admin123` (o `user@example.com` y
`user123`). Tras iniciar sesión, crea una orden con el asistente interactivo:

```cmd
poetry run orders-cli orders create --name "Cliente de prueba" --email "prueba@example.com"
poetry run orders-cli orders list
```

Usa el `order_id` que devuelva el comando create para consultar la orden. El
listado está vacío al iniciar si no hay órdenes guardadas:

```cmd
poetry run orders-cli orders get ORD-00001
```

Reemplaza `ORD-00001` por el ID real de tu orden. No ejecutes `delete` salvo que
quieras eliminar una orden existente.
