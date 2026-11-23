# Módulo 16 - Arquitectura Limpia

## Objetivo

Organizar el sistema con entidades, casos de uso, presenters, gateways, Unit of Work y eventos de dominio.

## Qué se realizó

- Entidades y eventos en `src/order_management/domain/`.
- Unit of Work y event bus en `src/order_management/application/`.
- Presenters JSON, CLI y auditoría.
- Adaptador SQLAlchemy de Unit of Work.
- Publicación del evento `OrderCreated`.
- Pruebas de arquitectura limpia en `tests/test_clean_arch.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_16
poetry install
poetry run python scripts/demo_module_16.py
poetry run pytest -q tests/test_clean_arch.py
```

El script muestra el caso de uso, UoW, eventos y presenters en memoria; no necesita
levantar la API, Docker ni Smocker. En esta carpeta no existe el endpoint
`/orders/tools/use-case`; ese endpoint pertenece a otra versión del proyecto.
Para arrancar la API CRUD de este módulo, de forma opcional:

```cmd
poetry run uvicorn order_management.api.main:app --reload
```

Abre `http://localhost:8000/docs`. Si el puerto 8000 está ocupado, agrega
`--port 8001` al comando y abre `http://localhost:8001/docs`.
Las rutas CRUD requieren autenticación: en Swagger usa **Authorize** e inicia
sesión con `admin@example.com` / `admin123` o `user@example.com` / `user123`.
