# Módulo 9 - APIs web con FastAPI

## Objetivo

Exponer operaciones CRUD de órdenes mediante FastAPI, JWT, Pydantic, CORS y documentación OpenAPI.

## Qué se realizó

- Aplicación FastAPI en `src/order_management/api/main.py`.
- Routers de autenticación y órdenes.
- Esquemas Pydantic y validación de datos.
- Login JWT y protección de endpoints.
- Pruebas de integración con la API.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_9
poetry install
poetry run alembic upgrade head
poetry run uvicorn order_management.api.main:app --reload
```

Documentación disponible al iniciar la API:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

Credenciales de prueba configuradas en el proyecto:

```text
admin@example.com / admin123
user@example.com / user123
```

En Swagger, pulsa **Authorize** e inicia sesión con una de estas cuentas para
probar las rutas protegidas de `/orders`. También puedes ejecutar `POST
/auth/login` con el formulario `username`/`password`; devuelve un JWT que debes
enviar como `Authorization: Bearer <token>`. Si el puerto 8000 está ocupado,
inicia la API con `--port 8001` y abre `http://localhost:8001/docs`.

Ejecutar pruebas:

```cmd
poetry run pytest -q
```
