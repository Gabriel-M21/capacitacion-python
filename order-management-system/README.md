# Order Management System

Servicio de gestión de órdenes de compra construido con **Arquitectura Hexagonal / Limpia**, implementado como proyecto final del learning path de Python.

## Tabla de contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Base de datos y migraciones](#base-de-datos-y-migraciones)
- [Ejecutar la API](#ejecutar-la-api)
- [CLI](#cli)
- [Pruebas](#pruebas)
- [Calidad de código](#calidad-de-código)
- [Docker](#docker)
- [CI/CD](#cicd)
- [Seguridad](#seguridad)
- [Endpoints de la API](#endpoints-de-la-api)
- [Auditoría de dependencias](#auditoría-de-dependencias)

---

## Descripción

Sistema CRUD de órdenes de compra que expone una API REST segura con JWT, una CLI interactiva y un modelo de dominio rico basado en Arquitectura Hexagonal y Limpia.

**Stack tecnológico:**

| Categoría | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12+ |
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x + Alembic |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Autenticación | JWT (python-jose) + bcrypt |
| Validación | Pydantic v2 + pydantic-settings |
| CLI | Typer + Rich |
| Testing | pytest + Hypothesis + pytest-cov |
| Calidad | black · ruff · isort · mypy · pre-commit |
| Contenedor | Docker multistage |
| CI/CD | GitHub Actions |

---

## Arquitectura

El proyecto implementa **Arquitectura Hexagonal (Puertos y Adaptadores)** combinada con principios de **Arquitectura Limpia**:

```
┌─────────────────────────────────────────────────────────────┐
│                    INFRAESTRUCTURA                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   APLICACIÓN                         │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │                  DOMINIO                       │  │    │
│  │  │  Order · Customer · OrderItem · Money         │  │    │
│  │  │  OrderStatus · Email · OrderId                │  │    │
│  │  │  OrderCreated · OrderStatusChanged (eventos)  │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │  CreateOrderUseCase · UnitOfWork · EventBus          │    │
│  │  Presenters (JSON · CLI · API · Audit)               │    │
│  └─────────────────────────────────────────────────────┘    │
│  OrderRepository (SQL) · InMemoryOrderRepository            │
│  HttpNotificationAdapter · InMemoryNotificationAdapter      │
│  SqlAlchemyUnitOfWork · FastAPI routers · CLI Typer         │
└─────────────────────────────────────────────────────────────┘
```

### Flujo del caso de uso CreateOrder

```
CreateOrderCommand
      │
      ▼
CreateOrderUseCase
      │
      ├─► UnitOfWork.orders.save(order)   ← persiste
      ├─► UnitOfWork.commit()             ← transacción atómica
      ├─► EventBus.publish(OrderCreated)  ← notifica handlers
      │         │
      │         ├─► NotificationHandler  → HTTP / email / SMS
      │         └─► AuditHandler         → log de auditoría
      │
      └─► Presenter.present(result)       ← formatea respuesta
                │
                ├─► JsonPresenter   → dict (API / webhook)
                ├─► CliPresenter    → texto (terminal)
                ├─► ApiPresenter    → OrderOut (FastAPI)
                └─► AuditPresenter → payload mínimo
```

### Puertos definidos

| Puerto | Implementaciones |
|--------|-----------------|
| `OrderRepositoryPort` | `OrderRepository` (SQL), `InMemoryOrderRepository` |
| `NotificationPort` | `HttpNotificationAdapter`, `InMemoryNotificationAdapter` |
| `UnitOfWorkPort` | `SqlAlchemyUnitOfWork`, `InMemoryUnitOfWork` |
| `OrderValidatorPort` | `OrderValidator` |
| `OrderPresenterPort` | `JsonPresenter`, `CliPresenter`, `ApiPresenter`, `AuditPresenter` |

---

## Estructura del proyecto

```
order-management-system/
├── src/order_management/
│   ├── domain/              # Núcleo — sin dependencias externas
│   │   ├── entities.py      # Order, Customer, OrderItem
│   │   ├── value_objects.py # Money, Email, OrderId, OrderStatus
│   │   ├── events.py        # OrderCreated, OrderStatusChanged
│   │   ├── ports.py         # Protocols (interfaces)
│   │   ├── pricing.py       # volume_discount (Strategy)
│   │   └── strategies.py    # PricingStrategy + implementaciones
│   │
│   ├── application/         # Casos de uso — orquesta sin I/O
│   │   ├── use_cases/
│   │   │   └── create_order.py
│   │   ├── dtos.py          # CreateOrderCommand, OrderCreatedResult
│   │   ├── unit_of_work.py  # UoW Protocol + InMemory
│   │   ├── event_bus.py     # EventBus (Observer)
│   │   └── presenters.py    # Formateo de resultados
│   │
│   ├── infrastructure/      # Adaptadores — detalles de implementación
│   │   ├── db/
│   │   │   ├── models.py    # UserModel, OrderModel, OrderItemModel
│   │   │   ├── session.py   # Engine + SessionLocal
│   │   │   └── repositories/
│   │   │       ├── order_repository.py      # SQLAlchemy
│   │   │       └── in_memory_order_repo.py  # En memoria
│   │   ├── adapters/
│   │   │   ├── http_notification.py    # HTTP POST
│   │   │   └── memory_notification.py  # En memoria
│   │   └── uow/
│   │       └── sqlalchemy_uow.py
│   │
│   ├── api/                 # Controladores HTTP (FastAPI)
│   │   ├── main.py          # App + CORS + routers
│   │   ├── dependencies.py  # get_db, get_current_user
│   │   ├── routers/
│   │   │   ├── auth.py      # POST /auth/login
│   │   │   └── orders.py    # CRUD /orders
│   │   └── security/
│   │       ├── jwt.py       # Crear/verificar tokens
│   │       └── users.py     # Gestión de usuarios
│   │
│   ├── cli/                 # CLI con Typer
│   │   ├── main.py          # Entry point: orders-cli
│   │   ├── auth.py          # login / logout / whoami
│   │   ├── orders.py        # list / get / create / delete / status
│   │   └── config.py        # Variables de entorno
│   │
│   ├── config/
│   │   └── settings.py      # pydantic-settings
│   │
│   ├── mappers/
│   │   └── order_mapper.py  # Domain ↔ API schemas
│   │
│   └── schemas/
│       └── schemas.py       # Pydantic schemas (OrderIn, OrderOut, etc.)
│
├── alembic/                 # Migraciones de base de datos
│   └── versions/            # 3 migraciones aplicadas
│
├── tests/                   # Suite de pruebas (146 tests)
│   ├── conftest.py
│   ├── test_api.py          # Integración FastAPI
│   ├── test_clean_arch.py   # UoW, EventBus, Presenters
│   ├── test_hexagonal.py    # Puertos y adaptadores
│   ├── test_orders_system.py # E2E integrador
│   ├── test_patterns.py     # Patrones de diseño
│   └── test_pricing.py      # TDD + Hypothesis
│
├── docs/
│   ├── pip-audit-report.json
│   └── pip-audit-report.md
│
├── Dockerfile               # Multistage build
├── .dockerignore
├── .github/workflows/ci.yml # Pipeline CI/CD
├── .env.example             # Variables de entorno plantilla
├── alembic.ini
└── pyproject.toml
```

---

## Requisitos

- Python 3.12+
- [Poetry](https://python-poetry.org/) >= 1.8
- Docker Desktop (opcional, para contenedor y Smocker)

---

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd order-management-system

# Instalar dependencias
poetry install

# Copiar variables de entorno
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

---

## Configuración

Edita `.env` antes de ejecutar en producción:

```env
# OBLIGATORIO cambiar en producción
SECRET_KEY=genera-con-python-c-import-secrets-print-secrets-token-hex-32

# Base de datos (SQLite por defecto, PostgreSQL para prod)
DATABASE_URL=sqlite:///order_management.db

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
```

Generar una clave segura:

```bash
poetry run python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Base de datos y migraciones

```bash
# Aplicar migraciones
poetry run alembic upgrade head

# Ver historial de migraciones
poetry run alembic history

# Crear nueva migración
poetry run alembic revision --autogenerate -m "descripción"
```

Migraciones incluidas:
1. `bda6c295ed89` — Crear tablas users, orders, order_items
2. `7e5d62d6fe39` — Añadir hashed_password y role (inicial, corregido)
3. `90582d06df97` — Añadir hashed_password y role a users (definitivo)

---

## Ejecutar la API

```bash
# Desarrollo con recarga automática
poetry run uvicorn order_management.api.main:app --reload

# Producción
poetry run uvicorn order_management.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Documentación interactiva disponible en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

---

## CLI

```bash
# Instalar entry point
poetry install

# Autenticación
poetry run orders-cli auth login --username admin@example.com --password admin123
poetry run orders-cli auth whoami
poetry run orders-cli auth logout

# Gestión de órdenes
poetry run orders-cli orders list
poetry run orders-cli orders list --status confirmed
poetry run orders-cli orders get ORD-00001
poetry run orders-cli orders create
poetry run orders-cli orders status ORD-00001 confirmed
poetry run orders-cli orders delete ORD-00001

# Configuración
poetry run orders-cli info
```

**Credenciales de prueba:**
- `admin@example.com` / `admin123`
- `user@example.com` / `user123`

**Variables de entorno de la CLI:**

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ORDERS_API_URL` | `http://localhost:8000` | URL base de la API |
| `ORDERS_API_TIMEOUT` | `10` | Timeout en segundos |
| `ORDERS_TOKEN_FILE` | `~/.orders-cli/token` | Ruta del token guardado |

---

## Pruebas

```bash
# Ejecutar toda la suite
poetry run pytest

# Con reporte de cobertura HTML
poetry run pytest --cov=src/order_management --cov-report=html
# Abrir: htmlcov/index.html

# Solo un archivo
poetry run pytest tests/test_orders_system.py -v

# Solo un bloque
poetry run pytest tests/test_orders_system.py::TestApiFastAPI -v
```

**Resumen de la suite (146 tests, 1 skipped):**

| Archivo | Tests | Qué cubre |
|---------|-------|-----------|
| `test_orders_system.py` | 34 | E2E integrador: dominio → caso de uso → DB → API |
| `test_patterns.py` | 31 | Strategy, Builder, Adapter, Decorator |
| `test_pricing.py` | 23 | TDD + property-based testing (Hypothesis) |
| `test_clean_arch.py` | 23 | UoW, EventBus, Presenters |
| `test_hexagonal.py` | 21 | Puertos, adaptadores, LSP |
| `test_api.py` | 14 | FastAPI endpoints + JWT |

**Cobertura total: 55%** — módulos críticos al 100%:
`create_order.py`, `events.py`, `presenters.py`, `unit_of_work.py`, `pricing.py`, `strategies.py`, `order_mapper.py`

---

## Calidad de código

```bash
# Formateo
poetry run black src/ tests/
poetry run isort src/ tests/

# Linting
poetry run ruff check --fix src/ tests/

# Tipado estático
poetry run mypy src/ scripts/

# Todo en uno (pre-commit)
poetry run pre-commit run --all-files
```

Los hooks de pre-commit se ejecutan automáticamente en cada `git commit`.

---

## Docker

```bash
# Build
docker build -t order-management:latest .

# Ejecutar
docker run -d \
  --name order-management \
  -p 8000:8000 \
  -e SECRET_KEY=tu-clave-segura \
  order-management:latest

# Verificar
curl http://localhost:8000/health
```

**Características del Dockerfile:**
- Build multistage (builder + runtime)
- Usuario no-root (`appuser`)
- Imagen base `python:3.12-slim`
- HEALTHCHECK integrado
- Sin Poetry en la imagen final

---

## CI/CD

Pipeline en `.github/workflows/ci.yml` con 5 jobs:

```
push/PR a main o develop
        │
        ▼
  ┌─────────────┐
  │   lint      │  ruff · black · isort
  └──────┬──────┘
         │
  ┌──────┴──────────────┐
  │                     │
  ▼                     ▼
  ┌─────────────┐  ┌─────────────┐
  │  typecheck  │  │    test     │
  │   (mypy)    │  │  (pytest)   │
  └──────┬──────┘  └──────┬──────┘
         └───────┬─────────┘
                 ▼
         ┌─────────────┐
         │    build    │  poetry build → wheel
         └──────┬──────┘
                ▼  (solo push a main)
         ┌─────────────┐
         │   docker    │  build + push → ghcr.io
         └─────────────┘
```

---

## Seguridad

- **Secretos**: gestionados con `pydantic-settings` — nunca hardcodeados
- **JWT**: tokens firmados con HS256, expiración configurable
- **Contraseñas**: hasheadas con bcrypt
- **Contenedor**: usuario no-root, imagen mínima
- **Dependencias**: auditadas con `pip-audit`
- **Pre-commit**: previene commits con código sin formatear

Generar SECRET_KEY seguro:
```bash
poetry run python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Endpoints de la API

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/auth/login` | ❌ | Obtener JWT |
| `GET` | `/orders` | ✅ | Listar órdenes |
| `POST` | `/orders` | ✅ | Crear orden |
| `GET` | `/orders/{id}` | ✅ | Obtener orden |
| `PATCH` | `/orders/{id}/status` | ✅ | Cambiar estado |
| `DELETE` | `/orders/{id}` | ✅ | Eliminar orden |

**Estados válidos y transiciones:**

```
pending → confirmed → processing → shipped → delivered
pending → cancelled
confirmed → cancelled
processing → cancelled
```

**Ejemplo de creación:**

```bash
# 1. Obtener token
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=admin123"

# 2. Crear orden
curl -X POST http://localhost:8000/orders \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {"name": "Juan Pérez", "email": "juan@example.com"},
    "items": [{"product_name": "Laptop", "quantity": 1, "unit_price": 1299.99}]
  }'
```

---

## Auditoría de dependencias

Ejecutada con `pip-audit`. Resultados en `docs/pip-audit-report.json`.

**Resumen del último escaneo:**

| Estado | Cantidad |
|--------|---------|
| Sin vulnerabilidades | 102 |
| Con vulnerabilidades (sin fix) | 2 |

**Hallazgos:**

| Paquete | CVE | Fix | Mitigación |
|---------|-----|-----|-----------|
| `ecdsa 0.19.2` | CVE-2024-23342 | No disponible | Dependencia transitiva de python-jose; solo se usa HS256, no ECDSA |
| `python-jose 3.5.0` | CVE-2026-85394 | No disponible | Algoritmo siempre especificado explícitamente (`algorithms=["HS256"]`) |

**Plan de remediación:** migrar de `python-jose` a `PyJWT` en la próxima iteración.

Ver reporte completo: `docs/pip-audit-report.md`

---

## Autor

Gabriel de Jesús Muñoz Ramírez — gabriel.munoz@axity.com
