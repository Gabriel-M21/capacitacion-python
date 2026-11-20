# Order Management System

Servicio de gestión de órdenes de compra construido con **Arquitectura Hexagonal / Limpia**, implementado como proyecto final del learning path de Python avanzado.

[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.165-green)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-149%20passed-brightgreen)](#pruebas)
[![Coverage](https://img.shields.io/badge/coverage-54%25-yellow)](#pruebas)
[![Docker](https://img.shields.io/badge/Docker-multistage-blue)](#docker)

---

## Tabla de contenidos

- [Order Management System](#order-management-system)
  - [Tabla de contenidos](#tabla-de-contenidos)
  - [Descripción](#descripción)
  - [Arquitectura](#arquitectura)
    - [Regla de dependencia](#regla-de-dependencia)
    - [Flujo del caso de uso CreateOrder](#flujo-del-caso-de-uso-createorder)
    - [Puertos (Protocols)](#puertos-protocols)
  - [Estructura del proyecto](#estructura-del-proyecto)
  - [Requisitos](#requisitos)
  - [Instalación y configuración](#instalación-y-configuración)
  - [Base de datos y migraciones](#base-de-datos-y-migraciones)
  - [Ejecución](#ejecución)
    - [API](#api)
  - [Verificación completa](#verificación-completa)
    - [Opción A — Script automatizado (recomendado)](#opción-a--script-automatizado-recomendado)
    - [Opción B — Script de endpoints en vivo](#opción-b--script-de-endpoints-en-vivo)
    - [Opción C — Manual paso a paso](#opción-c--manual-paso-a-paso)
  - [CLI](#cli)
  - [Pruebas](#pruebas)
  - [Calidad de código](#calidad-de-código)
  - [API — Endpoints](#api--endpoints)
    - [CRUD básico](#crud-básico)
  - [Endpoints de demostración (Herramientas)](#endpoints-de-demostración-herramientas)
  - [Docker](#docker)
  - [CI/CD](#cicd)
  - [Seguridad](#seguridad)
  - [Observabilidad](#observabilidad)
  - [Rendimiento](#rendimiento)
  - [Auditoría de dependencias](#auditoría-de-dependencias)
  - [Autor](#autor)

---

## Descripción

Sistema CRUD de órdenes de compra que expone:
- **API REST** segura con JWT y documentación Swagger automática
- **CLI interactiva** con Typer y Rich
- **Modelo de dominio rico** con Arquitectura Hexagonal y Limpia
- **Endpoints de demostración** que ejercitan cada módulo del learning path

**Stack tecnológico:**

| Categoría | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12+ |
| API | FastAPI 0.165 + Uvicorn |
| ORM | SQLAlchemy 2.x + Alembic |
| Base de datos | SQLite (configurada y validada) |
| Autenticación | JWT (python-jose) + bcrypt |
| Validación | Pydantic v2 + pydantic-settings |
| CLI | Typer + Rich |
| Testing | pytest + Hypothesis + pytest-cov |
| Calidad | black · ruff · isort · mypy · pre-commit |
| ML | scikit-learn + joblib + pandas + polars |
| Contenedor | Docker multistage |
| CI/CD | GitHub Actions |

---

## Arquitectura

El proyecto implementa **Arquitectura Hexagonal (Puertos y Adaptadores)** con principios de **Arquitectura Limpia**:

```
┌──────────────────────────────────────────────────────────────────┐
│                        INFRAESTRUCTURA                           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      APLICACIÓN                            │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │                     DOMINIO                          │  │  │
│  │  │  Order · Customer · OrderItem · Money                │  │  │
│  │  │  OrderStatus · Email · OrderId (Value Objects)       │  │  │
│  │  │  OrderCreated · OrderStatusChanged (Eventos)         │  │  │
│  │  │  OrderRepositoryPort · NotificationPort (Puertos)    │  │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  CreateOrderUseCase · UnitOfWork · EventBus                 │  │
│  │  Presenters: JSON · CLI · API · Audit                       │  │
│  │  DTOs: CreateOrderCommand · OrderCreatedResult              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  OrderRepository (SQL) · InMemoryOrderRepository                 │
│  HttpNotificationAdapter · InMemoryNotificationAdapter           │
│  SqlAlchemyUnitOfWork · InMemoryUnitOfWork                       │
│  FastAPI routers · Typer CLI · Settings (pydantic)               │
└──────────────────────────────────────────────────────────────────┘
```

### Regla de dependencia

```
Dominio ← Aplicación ← Infraestructura ← API / CLI
```

Ninguna capa interna importa de una capa externa. El dominio no conoce SQLAlchemy, FastAPI ni httpx.

### Flujo del caso de uso CreateOrder

```
CreateOrderCommand
      │
      ▼
CreateOrderUseCase (Application)
      │
      ├─► UoW.orders.save(order)      ← persiste (atómico)
      ├─► UoW.commit()                ← transacción
      ├─► EventBus.publish(OrderCreated)
      │         │
      │         ├─► NotificationHandler → HTTP / Smocker
      │         └─► AuditHandler        → log
      │
      └─► Presenter.present(result)
                ├─► JsonPresenter   → dict   (API/webhook)
                ├─► CliPresenter    → str    (terminal)
                ├─► ApiPresenter    → OrderOut (FastAPI)
                └─► AuditPresenter → dict   (auditoría)
```

### Puertos (Protocols)

| Puerto | Implementaciones |
|--------|-----------------|
| `OrderRepositoryPort` | `OrderRepository` (SQL), `InMemoryOrderRepository` |
| `NotificationPort` | `HttpNotificationAdapter`, `InMemoryNotificationAdapter` |
| `UnitOfWorkPort` | `SqlAlchemyUnitOfWork`, `InMemoryUnitOfWork` |
| `OrderValidatorPort` | `OrderValidator` |
| `OrderPresenterPort` | `JsonPresenter`, `CliPresenter`, `ApiPresenter`, `AuditPresenter` |
| `PricingStrategy` | `VolumeDiscountStrategy`, `SeasonalDiscountStrategy`, `VIPDiscountStrategy`, `MaxDiscountStrategy` |

---

## Estructura del proyecto

```
order-management-system/
├── src/order_management/
│   ├── domain/                    # Núcleo — sin dependencias externas
│   │   ├── entities.py            # Order, Customer, OrderItem
│   │   ├── value_objects.py       # Money, Email, OrderId, OrderStatus
│   │   ├── events.py              # OrderCreated, OrderStatusChanged
│   │   ├── ports.py               # Protocols (interfaces)
│   │   ├── pricing.py             # volume_discount (TDD)
│   │   └── strategies.py          # PricingStrategy + implementaciones
│   │
│   ├── application/               # Casos de uso — orquesta sin I/O
│   │   ├── use_cases/create_order.py
│   │   ├── dtos.py                # CreateOrderCommand, OrderCreatedResult
│   │   ├── unit_of_work.py        # UoW Protocol + InMemory
│   │   ├── event_bus.py           # EventBus (Observer)
│   │   └── presenters.py          # JSON · CLI · API · Audit
│   │
│   ├── infrastructure/            # Adaptadores
│   │   ├── db/
│   │   │   ├── models.py          # UserModel, OrderModel, OrderItemModel
│   │   │   ├── session.py         # Engine + SessionLocal (pydantic-settings)
│   │   │   └── repositories/
│   │   │       ├── order_repository.py
│   │   │       └── in_memory_order_repo.py
│   │   ├── adapters/
│   │   │   ├── http_notification.py
│   │   │   └── memory_notification.py
│   │   └── uow/sqlalchemy_uow.py
│   │
│   ├── api/                       # Controladores HTTP
│   │   ├── main.py                # App + CORS + middlewares
│   │   ├── dependencies.py        # get_db, get_current_user
│   │   ├── routers/
│   │   │   ├── auth.py            # POST /auth/login
│   │   │   └── orders.py          # CRUD + endpoints de demo
│   │   └── security/
│   │       ├── jwt.py
│   │       └── users.py
│   │
│   ├── cli/                       # CLI con Typer
│   │   ├── main.py                # Entry point: orders-cli
│   │   ├── auth.py
│   │   ├── orders.py
│   │   └── config.py              # Variables de entorno
│   │
│   ├── config/settings.py         # pydantic-settings centralizado
│   ├── mappers/order_mapper.py    # Domain ↔ API schemas
│   ├── schemas/schemas.py         # Pydantic schemas
│   └── services/
│       ├── order_builder.py       # Builder Pattern
│       └── order_validator.py     # SRP: solo valida
│
├── alembic/versions/              # 3 migraciones aplicadas
├── tests/                         # Suite unitaria, integración, contrato y E2E
│   ├── conftest.py
│   ├── test_api.py                # FastAPI + JWT + CORS
│   ├── test_clean_arch.py         # UoW, EventBus, Presenters
│   ├── test_hexagonal.py          # Puertos, LSP, adaptadores
│   ├── test_orders_system.py      # E2E integrador (34 tests)
│   ├── test_patterns.py           # Strategy, Builder, Adapter, Decorator
│   ├── test_pricing.py            # TDD + Hypothesis
│   └── test_validation_scripts.py # Auditoría: salida y vulnerabilidades
│
├── scripts/
│   ├── run_full_validation.py     # Valida todo el proyecto y genera reporte
│   └── verify_endpoints.py        # Ejecuta 37 comprobaciones HTTP en vivo
│
├── data/
│   ├── orders.json
│   ├── orders_extended.csv
│   └── output/order_classifier.joblib   # Modelo ML entrenado
│
├── docs/
│   ├── pip-audit-report.json
│   ├── pip-audit-report.md
│   └── validation_report.md
│
├── mocks/                         # Smocker YAML (módulo 7)
├── Dockerfile                     # Multistage build
├── .dockerignore
├── .github/workflows/ci.yml       # Pipeline GitHub Actions
├── .env.example
├── alembic.ini
└── pyproject.toml
```

---

## Requisitos

- Python 3.12+
- [Poetry](https://python-poetry.org/) >= 1.8
- Docker Desktop (para contenedor y tests de integración HTTP)

---

## Instalación y configuración

```bash
# 1. Clonar
git clone <url-del-repositorio>
cd order-management-system

# 2. Instalar dependencias
poetry install

# 3. Configurar variables de entorno
copy .env.example .env     # Windows
# cp .env.example .env     # Linux/macOS

# 4. Generar SECRET_KEY seguro
poetry run python -c "import secrets; print(secrets.token_hex(32))"
# Pegar el resultado en .env → SECRET_KEY=...
```

**Configuración recomendada en `.env`:**

```env
SECRET_KEY=pega-aqui-una-clave-de-64-caracteres-hex
DATABASE_URL=sqlite:///order_management.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
```

`SECRET_KEY` tiene un valor de desarrollo por defecto, pero la aplicación advierte
que es inseguro. Reemplázalo antes de cualquier despliegue. SQLite es la única base
de datos configurada y validada en este proyecto; PostgreSQL requiere añadir y
probar su driver antes de considerarlo soportado.

---

## Base de datos y migraciones

```bash
# Aplicar todas las migraciones
poetry run alembic upgrade head

# Ver historial
poetry run alembic history

# Crear nueva migración
poetry run alembic revision --autogenerate -m "descripcion"
```

**Migraciones incluidas:**

| Revisión | Descripción |
|----------|-------------|
| `bda6c295ed89` | Crear tablas `users`, `orders`, `order_items` |
| `7e5d62d6fe39` | Añadir `hashed_password` y `role` (revisión intermedia) |
| `90582d06df97` | `hashed_password` y `role` en `users` (definitivo) |

---

## Ejecución

### API

```bash
# Desarrollo con recarga automática
poetry run uvicorn order_management.api.main:app --reload

# Producción
poetry run uvicorn order_management.api.main:app \
  --host 0.0.0.0 --port 8000 --workers 4
```

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI interactivo |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/health` | Health check |

**Credenciales de prueba:**
- `admin@example.com` / `admin123`
- `user@example.com` / `user123`

---

## Verificación completa

### Opción A — Script automatizado (recomendado)

Ejecuta mypy, ruff, black, isort, pytest, pip-audit, docker build, Alembic y wheel:

```bash
poetry run python scripts/run_full_validation.py
```

Genera `docs/validation_report.md` con todos los resultados.

El reporte vigente (`docs/validation_report.md`, generado el 20-11-2026) registra
9/10 pasos exitosos: la auditoría encontró 2 hallazgos únicos en 2 paquetes tras
auditar 105 dependencias y omitir el paquete local. La auditoría ahora falla
correctamente ante vulnerabilidades. Las pruebas pasaron (150, 1 omitida), y
tipado, lint, formato, Docker, migraciones, empaquetado y health check pasaron.
La comprobación de salud usa el mismo `ORDERS_API_URL` que el script de endpoints.

### Opción B — Script de endpoints en vivo

Con la API corriendo, ejecuta **37 comprobaciones HTTP** (casos positivos,
negativos y varias entradas; no son 37 rutas únicas):

```bash
# Terminal 1
poetry run uvicorn order_management.api.main:app --reload

# Terminal 2
poetry run python scripts/verify_endpoints.py
```

El script usa `ORDERS_API_URL` o, si no está definida, `http://localhost:8000`.
En CMD, para probar otro puerto:

```cmd
set ORDERS_API_URL=http://localhost:8001
poetry run python scripts/verify_endpoints.py
```

Ejecución reportada el 20-11-2026 contra `localhost:8000`: **37 pasaron, 0
fallaron y 0 se omitieron** en 9.22 s. Después se reforzó el script para validar
también los porcentajes de descuento; vuelve a ejecutarlo para actualizar esa
evidencia. El chequeo ML/CSV requiere que existan el modelo y el CSV de muestra.

Resumen:
```
Total comprobaciones HTTP   : 37
Pasaron                     : 37
Fallaron                    : 0
Omitidos                    : 0
Resultado: 100% de comprobaciones HTTP correctas
```

### Opción C — Manual paso a paso

```bash
poetry run mypy src/ scripts/ tests/
poetry run ruff check src/ scripts/ tests/
poetry run black --check src/ scripts/ tests/
poetry run isort --check-only src/ scripts/ tests/
poetry run pytest -v                        # última ejecución: 150 passed, 1 skipped
poetry run pre-commit run --all-files
```

Para instalar los hooks y ejecutarlos automáticamente al hacer commit:

```bash
poetry run pre-commit install
```

---

## CLI

```bash
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
poetry run orders-cli orders delete ORD-00001 --force

# Configuración
poetry run orders-cli info
```

**Variables de entorno de la CLI:**

| Variable | Default | Descripción |
|----------|---------|-------------|
| `ORDERS_API_URL` | `http://localhost:8000` | URL base de la API |
| `ORDERS_API_TIMEOUT` | `10` | Timeout en segundos |
| `ORDERS_TOKEN_FILE` | `~/.orders-cli/token` | Token persistido en disco |

---

## Pruebas

```bash
# Suite completa
poetry run pytest -v

# Con cobertura HTML
poetry run pytest --cov=src/order_management --cov-report=html
# Abrir: htmlcov/index.html

# Por archivo
poetry run pytest tests/test_orders_system.py -v
poetry run pytest tests/test_orders_system.py::TestApiFastAPI -v
```

**Última ejecución local:** 150 passed, 1 skipped, 7 warnings y 54% de cobertura
con `poetry run pytest -q`. `docs/validation_report.md` es un reporte anterior;
vuelve a ejecutar `poetry run python scripts/run_full_validation.py` para
actualizarlo antes de la entrega.

| Archivo | Tipo | Qué cubre |
|---------|------|-----------|
| `test_orders_system.py` | E2E integrador | Dominio → Caso de uso → DB → API |
| `test_patterns.py` | Unitario | Strategy, Builder, Adapter, Decorator |
| `test_pricing.py` | TDD + Hypothesis | `volume_discount` y propiedades |
| `test_clean_arch.py` | Unitario | UoW, EventBus, Presenters |
| `test_hexagonal.py` | Contrato | Puertos, LSP, adaptadores HTTP |
| `test_api.py` | Integración | Auth, health, CORS y CRUD FastAPI + JWT |
| `test_validation_scripts.py` | Unitario | Auditoría ante salida inválida y hallazgos |

**Cobertura total en la última ejecución: 54%**

Los endpoints de demostración se verifican por separado con
`scripts/verify_endpoints.py`; esa comprobación en vivo no sustituye pruebas
automatizadas de integración dentro de pytest.

**Tipos de prueba:**

- **Unitarias**: dominio puro sin infraestructura (`TestDominioPuro`)
- **De contrato (LSP)**: verifican que adaptadores son intercambiables (`test_contrato_lsp_*`)
- **De integración**: API con SQLite real (`TestApiFastAPI`)
- **E2E**: flujo completo dominio → UoW → DB → API (`TestFlujoCompletoE2E`)
- **Property-based**: pruebas basadas en propiedades con Hypothesis (`test_pricing.py`)

---

## Calidad de código

```bash
poetry run black src/ scripts/ tests/           # formato
poetry run isort src/ scripts/ tests/           # imports
poetry run ruff check --fix src/ scripts/ tests/ # linting
poetry run mypy src/ scripts/ tests/            # tipado estático
poetry run pre-commit run --all-files           # hooks configurados
```

**Herramientas configuradas:** mypy, ruff, black e isort. Los resultados de la
última ejecución registrada se encuentran en `docs/validation_report.md`; ese
reporte es histórico y debe regenerarse antes de la entrega.

Los hooks de pre-commit solo se ejecutan automáticamente después de instalarse
con `poetry run pre-commit install`. Los hooks actuales verifican formato e
integridad de archivos, pero no detectan secretos.

---

## API — Endpoints

### CRUD básico

| Método | Ruta | Auth | Descripción |
|--------|------|:----:|-------------|
| `GET` | `/health` | No | Health check |
| `POST` | `/auth/login` | No | Obtener JWT |
| `GET` | `/orders` | Sí | Listar todas las órdenes |
| `POST` | `/orders` | Sí | Crear orden |
| `GET` | `/orders/{id}` | Sí | Obtener orden por ID |
| `PATCH` | `/orders/{id}/status` | Sí | Cambiar estado |
| `DELETE` | `/orders/{id}` | Sí | Eliminar orden |

**Estados y transiciones válidas:**

```
pending → confirmed → processing → shipped → delivered
       ↘            ↘            ↘
        cancelled    cancelled    cancelled
```

**Ejemplo rápido:**

```bash
# Bash / Git Bash: obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=admin123" \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Crear orden
curl -X POST http://localhost:8000/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": {"name": "Juan Pérez", "email": "juan@example.com"},
    "items": [{"product_name": "Laptop", "quantity": 1, "unit_price": 1299.99}]
  }'
```

En CMD, el ejemplo de Bash anterior no aplica. Solicita el token y pégalo en la
variable `TOKEN`:

```cmd
curl.exe -s -X POST http://localhost:8000/auth/login -d "username=admin@example.com&password=admin123"
set "TOKEN=pega-aqui-el-access_token"
curl.exe -s "http://localhost:8000/orders/tools/capabilities" -H "Authorization: Bearer %TOKEN%"
```

---

## Endpoints de demostración (Herramientas)

Todos requieren autenticación JWT. Accesibles desde Swagger: `http://localhost:8000/docs`

| Método | Ruta | Módulo | Qué demuestra |
|--------|------|--------|---------------|
| `GET` | `/orders/tools/volume-discount/{n}` | 10 | TDD: descuento por volumen |
| `GET` | `/orders/tools/concurrency-benchmark` | 11 | Async vs sync benchmark |
| `POST` | `/orders/tools/validate` | 12 | SOLID: validar sin persistir |
| `POST` | `/orders/tools/pricing-strategy` | 13 | Strategy de precios |
| `POST` | `/orders/tools/builder` | 13 | Builder Pattern |
| `POST` | `/orders/tools/ml-inference` | 14 | ML: predecir estado (joblib) |
| `GET` | `/orders/tools/csv-metrics` | 14 | Pandas: métricas del CSV |
| `POST` | `/orders/tools/use-case` | 15/16 | Hexagonal: UoW + EventBus + Presenter |
| `GET` | `/orders/tools/capabilities` | — | Mapa de todos los endpoints |

**Ejemplo — benchmark de concurrencia (Módulo 11):**

```bash
curl "http://localhost:8000/orders/tools/concurrency-benchmark?n_orders=50" \
  -H "Authorization: Bearer $TOKEN"
# → {"sync_time_s": 0.079, "async_time_s": 0.010, "speedup": 8.06}
```

**Ejemplo — ML inference (Módulo 14):**

```bash
curl -X POST http://localhost:8000/orders/tools/ml-inference \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_total": 1500, "item_count": 2, "hour": 10, "day_of_week": 1, "month": 3}'
# → {"prediction": "confirmed", "confidence": 0.3414}
```

---

## Docker

```bash
# Build
docker build -t order-management:latest .

# Ejecutar
docker run -d \
  --name order-management \
  -p 8000:8000 \
  -e SECRET_KEY=tu-clave-de-64-chars \
  -e DATABASE_URL=sqlite:////app/data/orders.db \
  order-management:latest

# Verificar
curl http://localhost:8000/health
```

**Características del Dockerfile multistage:**

| Stage | Rol |
|-------|-----|
| `builder` | Instala Poetry, resuelve deps, genera wheel |
| `runtime` | Imagen mínima: pip instala wheel, usuario no-root |

- Base: `python:3.12-slim`
- Usuario: `appuser` (uid 1001, no-root)
- HEALTHCHECK integrado
- Sin Poetry en la imagen final
- Tamaño: ~1 GB (incluye pandas, scikit-learn, polars)

El contexto Docker excluye `data/` mediante `.dockerignore`; por ello, el contenedor
no incluye `orders_extended.csv` ni `order_classifier.joblib`. Los endpoints
`/orders/tools/csv-metrics` y `/orders/tools/ml-inference` responderán 404 dentro
del contenedor mientras no se monten o incluyan esos archivos.

---

## CI/CD

Pipeline en `.github/workflows/ci.yml` con 5 jobs:

```
push / PR a main o develop
          │
          ▼
    ┌───────────┐
    │   lint    │  ruff · black · isort
    └─────┬─────┘
          │
    ┌─────┴──────────────┐
    ▼                    ▼
┌──────────┐       ┌──────────┐
│typecheck │       │   test   │
│ (mypy)   │       │ (pytest) │
└─────┬────┘       └────┬─────┘
      └──────┬──────────┘
             ▼
      ┌────────────┐
      │   build    │  poetry build → wheel + sdist
      └──────┬─────┘
             ▼  (solo push a main)
      ┌────────────┐
      │   docker   │  build + push → ghcr.io
      └────────────┘
```

**Jobs:**
1. **lint** — ruff, black, isort
2. **typecheck** — mypy (paralelo con test)
3. **test** — pytest con cobertura mínima 30%
4. **build** — genera wheel y sdist, sube artefactos
5. **docker** — build + push a `ghcr.io/{repo}` (solo `main`)

---

## Seguridad

| Práctica | Implementación |
|----------|---------------|
| Secretos | `pydantic-settings` lee el entorno; el valor de desarrollo por defecto es inseguro |
| JWT | HS256, algoritmo siempre especificado explícitamente |
| Contraseñas | bcrypt con salt automático |
| Contenedor | Usuario no-root (`appuser`), imagen mínima slim |
| Dependencias | Reporte local `pip-audit`; no está integrado en el workflow CI |
| Pre-commit | Hooks de formato y validación; no incluye detector de secretos |
| `.env` | En `.gitignore`, plantilla en `.env.example` |
| CORS | Orígenes configurables con `CORS_ORIGINS`; por defecto permite localhost |

```bash
# Generar SECRET_KEY seguro (256 bits de entropía)
poetry run python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Observabilidad

El sistema usa el módulo estándar `logging` de Python. Hay llamadas de log en
casos de uso, EventBus, adaptadores y utilidades; no hay salida JSON estructurada,
métricas Prometheus ni trazas distribuidas configuradas.

**Loggers configurados por capa:**

| Logger | Módulo | Qué registra |
|--------|--------|-------------|
| `order_management.application.event_bus` | Aplicación | Publicación y manejo de eventos |
| `order_management.application.use_cases.create_order` | Aplicación | Ejecución del caso de uso |
| `order_management.infrastructure.adapters.http_notification` | Infraestructura | Notificaciones HTTP |
| `order_management.clients` / `order_management.utils` | Clientes y utilidades | Caché, reintentos y procesamiento |

**Niveles en uso:**

```python
logger.info("CreateOrder completado — %s", order.order_id)
logger.warning("Notificación fallida (no crítico): %s", exc)
logger.error("Error en procesamiento: %s", exc)
```

**Configuración básica:**

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

**Ver logs en tiempo real:**

```bash
# Con la API corriendo
poetry run uvicorn order_management.api.main:app --reload --log-level info

# En Docker
docker logs -f order-management
```

---

## Rendimiento

Resultados medidos con el endpoint `/orders/tools/concurrency-benchmark`.
El endpoint simula I/O con `asyncio.sleep`; estas cifras ilustran concurrencia y
no representan una prueba de carga de producción.

**Comparación async vs sync (Módulo 11):**

| Tareas | Tiempo sync | Tiempo async | Speedup |
|--------|------------|-------------|---------|
| 5 | 0.0072s | 0.0074s | 0.98x (overhead supera ganancia) |
| 50 | 0.0793s | 0.0098s | **8.06x** |

**Conclusión:** asyncio es significativamente más eficiente para I/O-bound con suficientes tareas concurrentes. El overhead de crear corrutinas solo se amortiza a partir de ~10 tareas.

**Fetcher HTTP del catálogo (Módulo 7, con Smocker):**

| Estrategia | Tiempo (60 productos) |
|------------|----------------------|
| Síncrono (httpx.Client) | 0.540s |
| Asíncrono (semáforo=10) | 0.592s |

En localhost la diferencia es mínima — con latencia real de red (>50ms/req) asyncio muestra speedup de 5-10x.

**CPU-bound (Módulo 11):**

| Estrategia | 34,000 cálculos |
|------------|----------------|
| Secuencial (1 proceso) | 0.098s |
| ProcessPoolExecutor (12 CPUs) | 1.422s |

Para operaciones triviales, el overhead de serialización entre procesos supera la ganancia — `ProcessPoolExecutor` solo vale para cálculos de >1 segundo por tarea.

---

## Auditoría de dependencias

Ejecutada con `pip-audit`. Ver reporte completo en `docs/pip-audit-report.md`.

```bash
# Re-ejecutar auditoría
poetry run pip-audit --format json -o docs/pip-audit-report.json
poetry run pip-audit > docs/pip-audit-report.txt
```

**Resumen del último escaneo local** (`docs/pip-audit-report.md`, 20-11-2026;
repítelo si cambian las dependencias, porque depende de las versiones instaladas):

| Métrica | Valor |
|---------|-------|
| Registros en JSON | 106 |
| Dependencias auditadas | 105 |
| Omitida (paquete local) | 1 |
| Sin vulnerabilidades | 103 |
| Paquetes con vulnerabilidades sin fix | 2 |
| Entradas de hallazgo (2 IDs únicos) | 3 |

**Hallazgos y mitigaciones:**

| Paquete | CVE | Fix | Mitigación aplicada |
|---------|-----|-----|---------------------|
| `ecdsa 0.19.2` | CVE-2024-23342 | No disponible | Transitiva de python-jose; no se invoca directamente. El hallazgo sigue abierto. |
| `python-jose 3.5.0` | CVE-2026-85394 | No disponible | Se restringe a HS256; pip-audit sigue reportando la dependencia vulnerable. |

**Plan de remediación:** evaluar la migración de `python-jose` a `PyJWT` y volver
a ejecutar la auditoría. La configuración actual limita JWT a HS256, pero no
elimina los hallazgos del escaneo ni sustituye una actualización de dependencia.

---

## Autor

**Gabriel de Jesús Muñoz Ramírez**
gabriel.munoz@axity.com
