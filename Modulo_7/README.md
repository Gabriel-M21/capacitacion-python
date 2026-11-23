# Módulo 7 - HTTP y consumo de APIs con Smocker

## Objetivo

Crear clientes HTTP robustos con timeouts, reintentos y manejo controlado de errores.

## Qué se realizó

- Cliente HTTP con `httpx` en `src/order_management/clients/catalog_client.py`.
- Configuración de timeout y reintentos.
- Manejo de respuestas y errores de red.
- Descarga de archivos por streaming.
- Respuestas simuladas de catálogo y exportación en los YAML de `mocks/`.
- Demostración que compara precios de las órdenes con el catálogo en `scripts/demo_module_7.py`.

## Preparar Smocker en Windows

La demo espera el servidor de mocks en `http://localhost:8080`. Smocker tiene dos
puertos: `8080` recibe las llamadas simuladas y `8081` permite registrar mocks y
abrir su interfaz web. Se requiere Docker Desktop instalado y en ejecución.

Abre **CMD** en la carpeta `Modulo_7`. Si aún no existe el contenedor, créalo:

```cmd
docker run -d --name smocker -p 8080:8080 -p 8081:8081 ghcr.io/smocker-dev/smocker
```

Si el contenedor `smocker` ya existe y está detenido, inícialo; si está activo,
continúa al siguiente paso sin volver a ejecutar `docker run`:

```cmd
docker start smocker
```

Confirma que Smocker está listo. El comando debe devolver información de versión:

```cmd
curl.exe http://localhost:8081/version
```

## Registrar los mocks del proyecto

Desde la misma carpeta `Modulo_7`, carga **los tres archivos** YAML. Cada
solicitud los registra en el servidor:

```cmd
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\catalog.yml" http://localhost:8081/mocks
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\catalog_products.yml" http://localhost:8081/mocks
curl.exe -X POST -H "Content-Type: application/x-yaml" --data-binary "@mocks\download.yml" http://localhost:8081/mocks
```

Los archivos definen respuestas `GET /products/...` y `GET /exports/catalog.json`.
Puedes revisar y administrar los mocks desde `http://localhost:8081/`.
Comprueba las rutas con el puerto de servicio:

```cmd
curl.exe -i http://localhost:8080/products/SKU-001
curl.exe -i "http://localhost:8080/products/Laptop%20Dell%20XPS%2015"
curl.exe -i http://localhost:8080/exports/catalog.json
```

Si guardas el comando en un archivo `.cmd`, escapa los signos `%` duplicándolos:

```bat
curl.exe -i "http://localhost:8080/products/Laptop%%20Dell%%20XPS%%2015"
```

## Ejecutar la demostración

Con Smocker en ejecución y los YAML registrados, abre otra consola **CMD** en
`Modulo_7`:

```cmd
poetry install
poetry run python scripts/demo_module_7.py
```

La demo lee `data/orders.json`, consulta los productos en Smocker y guarda la
descarga de catálogo en `data/output/catalog_download.json`.

### Reiniciar o detener Smocker

Para borrar los mocks registrados, sin destruir el contenedor:

```cmd
curl.exe -X POST http://localhost:8081/reset
```

Después de un reset, vuelve a registrar los tres YAML con los comandos anteriores.
Para detener el contenedor:

```cmd
docker stop smocker
```
