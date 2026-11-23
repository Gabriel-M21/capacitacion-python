# Módulo 11 - Concurrencia y rendimiento

## Objetivo

Comparar ejecución síncrona y asincrónica y mostrar cuándo `asyncio` aporta beneficio.

## Qué se realizó

- Demostración de tareas asíncronas y síncronas.
- Medición de tiempos con operaciones simuladas.
- Comparación de throughput y aceleración.
- Script `scripts/demo_module_11.py`.

## Ejecución

La demostración consulta el catálogo por HTTP y requiere Smocker, además de
`data/orders.json`. Abre CMD en la raíz del repositorio y ejecuta:

```cmd
cd /d Modulo_11
poetry install
```

Si todavía no existe el contenedor compartido `smocker`, créalo (la primera vez
Docker puede necesitar descargar la imagen):

```cmd
docker run -d --name smocker -p 8080:8080 -p 8081:8081 ghcr.io/smocker-dev/smocker
```

Si ya existe el contenedor, no ejecutes `docker run` otra vez: usa
`docker start smocker` si está detenido; si ya está activo, continúa. Comprueba
que responde en `http://localhost:8081/version`:

```cmd
curl.exe http://localhost:8081/version
```

Si estos YAML aún no están registrados en ese servidor, cárgalos desde la carpeta
`Modulo_11`:

```cmd
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\catalog.yml" http://localhost:8081/mocks
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\catalog_products.yml" http://localhost:8081/mocks
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\download.yml" http://localhost:8081/mocks
```

Ejecuta la comparación síncrona/asíncrona y el cálculo con procesos:

```cmd
poetry run python scripts/demo_module_11.py
```

La demo consulta `http://localhost:8080` y lee `data/orders.json`. No necesita
levantar la API FastAPI: este módulo todavía no expone un endpoint de benchmark.
Si el puerto 8080 ya lo usa otro servicio, detén ese servicio o ajusta el servidor
mock y `SMOCKER_URL` en el código antes de correr la demo.

La instalación de Smocker y los YAML se describen con más detalle en
[`Modulo_7/README.md`](../Modulo_7/README.md); ejecuta los comandos estando dentro
de `Modulo_11` para cargar los mocks de esta versión del proyecto. Si ya registraste
estos mismos YAML en el servidor usado por el Módulo 7, no hace falta volver a
registrarlos. Detén `smocker` con `docker stop smocker` sólo si ningún otro módulo
lo está usando.
