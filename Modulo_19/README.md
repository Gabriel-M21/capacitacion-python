# Módulo 19 - Seguridad y mantenimiento

## Objetivo

Centralizar configuración sensible, proteger secretos, auditar dependencias y revisar el hardening del contenedor.

## Qué se realizó

- Configuración con Pydantic Settings en `src/order_management/config/settings.py`.
- Plantilla de variables en `.env.example`.
- Validación de `SECRET_KEY` y tiempo de expiración.
- Configuración de CORS mediante variables de entorno.
- Auditoría de paquetes con `pip-audit`.
- Revisión de Docker sin root y buenas prácticas de contenedor.
- Script demostrativo `scripts/demo_module_19.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_19
poetry install
if not exist .env copy .env.example .env
poetry run python scripts/demo_module_19.py
```

La demo es local: muestra la configuración, audita las dependencias y revisa el
Dockerfile; no necesita iniciar la API, Smocker ni Docker. `pip-audit` requiere
acceso a internet para consultar los avisos de seguridad. Para una clave local,
genera el valor y pégalo en `SECRET_KEY` dentro de `.env`:

```cmd
poetry run python -c "import secrets; print(secrets.token_hex(32))"
notepad .env
```

No uses valores de desarrollo en producción y no compartas ni subas `.env`.

Ejecutar la auditoría directamente:

```cmd
poetry run pip-audit --format json --progress-spinner off
```

Comandos de validación recomendados:

```cmd
poetry run pytest -q
poetry run mypy src/
poetry run ruff check src/ scripts/ tests/
```

## Docker: construir y ejecutar la imagen

El Dockerfile es multistage: compila el wheel en la etapa `builder` y produce una
imagen final `runtime` basada en `python:3.12-slim`, sin Poetry ni dependencias de
desarrollo. `.dockerignore` excluye `.env`, tests, scripts, datos, mocks y cachés;
por tanto, los secretos no se copian a la imagen y la demo CSV/ML no queda
incluida. El Dockerfile no contiene una base PostgreSQL ni un servicio Smocker.

Abre Docker Desktop, espera a que el motor indique que está en ejecución y usa la
misma consola CMD que está en `Modulo_19`. Primero configura una clave para esta
ejecución local: reemplaza el valor de `SECRET_KEY` en `.env` por una clave
generada como se indicó arriba. No uses la clave de ejemplo en despliegues reales.

Construye y etiqueta la imagen desde la carpeta que contiene el Dockerfile:

```cmd
docker build -t order-management:module19 .
```

La primera compilación descarga la imagen base e instala dependencias, así que
requiere conexión a internet y puede tardar varios minutos. Confirma que la imagen
se creó:

```cmd
docker image ls order-management
```

Opcionalmente, construye y etiqueta sólo la etapa intermedia para inspeccionar el
multistage build:

```cmd
docker build --target builder -t order-management:module19-builder .
```

### Ejecutar la API y conservar la base SQLite

El contenedor escucha en el puerto `8000`; el ejemplo publica el servicio en el
puerto local `8001` para evitar conflictos. Un volumen con nombre conserva la base
SQLite aunque se elimine el contenedor. `.env` se entrega al proceso en tiempo de
ejecución y no forma parte de la imagen:

```cmd
docker volume create orders-data
docker run -d --name orders-api -p 8001:8000 --env-file .env -e DATABASE_URL=sqlite:////app/data/order_management.db -v orders-data:/app/data order-management:module19
```

Comprueba el estado del contenedor y del health check:

```cmd
docker ps
docker inspect --format "{{.State.Health.Status}}" orders-api
docker exec orders-api whoami
```

El health check debe indicar `healthy` cuando la aplicación haya terminado de
iniciar; `whoami` debe mostrar `appuser`, el usuario sin privilegios definido por
el Dockerfile. Consulta la API desde CMD:

```cmd
curl.exe -i http://localhost:8001/health
```

Abre `http://localhost:8001/docs` para probar la API. Las rutas de órdenes
requieren JWT: usa **Authorize** y las credenciales locales `admin@example.com` /
`admin123` o `user@example.com` / `user123`.

Para ver los logs en tiempo real (Ctrl+C sólo termina el seguimiento, no el
contenedor):

```cmd
docker logs -f --tail 50 orders-api
```

Si `docker run` informa que el nombre `orders-api` ya está en uso, revisa los
contenedores existentes:

```cmd
docker ps -a --filter name=orders-api
```

Si sólo quieres reiniciar el contenedor existente, usa `docker start orders-api`.
Para aplicar una imagen recién construida, primero detén y elimina el contenedor
antiguo con los comandos de limpieza de abajo y después repite `docker run`.

### Detener y limpiar

Detén y elimina el contenedor cuando termines. El volumen `orders-data` se
conserva, por lo que las órdenes SQLite seguirán ahí si vuelves a crear el
contenedor con el mismo volumen:

```cmd
docker stop orders-api
docker rm orders-api
```

Para iniciarlo de nuevo, repite el comando `docker run` anterior. Para borrar la
imagen:

```cmd
docker image rm order-management:module19
```

Sólo si también quieres eliminar permanentemente la base de datos guardada, borra
el volumen:

```cmd
docker volume rm orders-data
```
