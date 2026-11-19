# =============================================================================
# Dockerfile multistage - Módulo 17: Empaquetado y distribución
# =============================================================================
# Stage 1 (builder): instala Poetry, resuelve dependencias y genera el wheel
# Stage 2 (runtime): imagen mínima con solo lo necesario para producción
#
# Uso:
#   docker build -t order-management:latest .
#   docker run -p 8000:8000 order-management:latest
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1 — builder
# Instala Poetry, exporta dependencias y construye el wheel del paquete
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Instalar Poetry
RUN pip install "poetry==$POETRY_VERSION"
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /build

# Copiar solo los archivos de dependencias primero (mejor cache de capas)
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias de producción (sin dev) en el virtualenv local
RUN poetry install --only main --no-root

# Copiar el código fuente e instalar el paquete
COPY src/ ./src/
COPY README.md ./

# Construir el wheel del paquete
RUN poetry build --format wheel

# Exportar requirements.txt para instalar en runtime sin Poetry
RUN poetry export --only main --without-hashes -f requirements.txt \
    -o /build/requirements.txt

# -----------------------------------------------------------------------------
# STAGE 2 — runtime
# Imagen mínima: Python + dependencias instaladas con pip + usuario no-root
# No incluye Poetry ni herramientas de desarrollo
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    APP_PORT=8000

# Crear usuario no-root para seguridad
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR $APP_HOME

# Instalar dependencias de producción directamente con pip del sistema
# (evita copiar el .venv del builder que puede tener paths incompatibles)
COPY --from=builder /build/requirements.txt ./
RUN pip install -r requirements.txt

# Instalar el wheel del paquete
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Copiar archivos de configuración necesarios en runtime
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Crear directorio de datos y logs con permisos correctos
RUN mkdir -p data/output logs && \
    chown -R appuser:appgroup $APP_HOME

# Cambiar al usuario no-root
USER appuser

# Puerto de la aplicación
EXPOSE $APP_PORT

# Health check usando urllib de la stdlib (sin dependencias externas)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

# Comando por defecto: levantar FastAPI con uvicorn
CMD ["uvicorn", "order_management.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
