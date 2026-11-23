# Módulo 17 - Empaquetado, distribución y CI/CD

## Objetivo

Generar artefactos reproducibles, contenerizar la API y automatizar calidad y entrega.

## Qué se realizó

- Construcción de wheel con Poetry.
- Dockerfile multistage para FastAPI.
- Usuario no-root dentro del contenedor.
- Workflow de GitHub Actions para validaciones.
- Demo automatizada de empaquetado y ejecución del contenedor en `scripts/demo_module_17.py`.

## Ejecución

Abre CMD en la raíz del repositorio y entra al módulo. Se requiere Python 3.12,
Poetry, acceso a internet la primera vez y Docker Desktop instalado con el motor
de Docker en ejecución.

```cmd
cd /d Modulo_17
poetry install
```

Construir el wheel:

```cmd
poetry build
```

Construir la imagen y levantar la API. Se usa el puerto local 8001 para evitar
conflictos con servicios que ya ocupen el 8000:

```cmd
docker build -t order-management:module17 .
docker run --rm --name order-management-module17 -p 8001:8000 order-management:module17
```

Mientras el contenedor está en ejecución, abre otra consola:

```cmd
curl.exe http://localhost:8001/health
```

Presiona Ctrl+C en la consola del contenedor para detenerlo. También puedes
ejecutar la demostración automatizada, que genera el wheel, construye y prueba la
imagen:

```cmd
poetry run python scripts/demo_module_17.py
```

Nota: el script de demostración borra `dist/` antes de construir el wheel y
elimina cualquier contenedor llamado `order-management-demo`. No lo ejecutes si
necesitas conservar ese directorio o contenedor. Las pruebas del módulo se pueden
correr sin Docker:

```cmd
poetry run pytest -q
```
