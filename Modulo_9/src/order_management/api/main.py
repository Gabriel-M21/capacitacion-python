"""
Aplicación FastAPI principal - Módulo 9: APIs web con FastAPI
Configura CORS, routers y la documentación OpenAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from order_management.api.routers import auth, orders
from order_management.api.security.users import seed_users
from order_management.infrastructure.db import models  # noqa: F401
from order_management.infrastructure.db.base import Base
from order_management.infrastructure.db.session import SessionLocal, engine

# Crear tablas si no existen (para desarrollo)
# En producción se usa exclusivamente Alembic
Base.metadata.create_all(bind=engine)

# Crear usuarios de prueba si no existen
with SessionLocal() as _db:
    seed_users(_db)

app = FastAPI(
    title="Order Management API",
    description=(
        "API REST para gestión de órdenes de compra.\n\n"
        "## Autenticación\n"
        "Usa JWT Bearer token. Obtén tu token en `/auth/login`.\n\n"
        "**Credenciales de prueba:**\n"
        "- `admin@example.com` / `admin123`\n"
        "- `user@example.com` / `user123`\n\n"
        "## Endpoints\n"
        "- **Auth**: login y obtención de token\n"
        "- **Orders**: CRUD completo de órdenes"
    ),
    version="1.0.0",
    contact={
        "name": "Order Management Team",
        "email": "dev@example.com",
    },
    license_info={
        "name": "MIT",
    },
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: lista de dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(orders.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Sistema"], summary="Health check")
def health_check() -> dict[str, str]:
    """Verifica que la API está en línea."""
    return {"status": "ok", "service": "order-management-api"}
