"""Cliente HTTP para consultar el catálogo de productos."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from order_management.schemas.schemas import CatalogProductOut

logger = logging.getLogger(__name__)


class CatalogProductNotFound(Exception):
    """El producto solicitado no existe en el catálogo."""


class CatalogRequestError(Exception):
    """Falló la comunicación con el servicio de catálogo."""


class CatalogClient:
    """Cliente asíncrono con timeout, reintentos y descarga por streaming."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        transport: Any | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries no puede ser negativo")
        if backoff_factor < 0:
            raise ValueError("backoff_factor no puede ser negativo")

        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )

    async def __aenter__(self) -> "CatalogClient":
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Cierra el cliente HTTP y libera sus conexiones."""
        await self._client.aclose()

    async def get_product(self, product_id: str) -> CatalogProductOut:
        """Obtiene y valida un producto por su ID."""
        encoded_id = quote(product_id, safe="")
        url = f"/products/{encoded_id}"

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url)

                if response.status_code == 404:
                    raise CatalogProductNotFound(f"No existe el producto '{product_id}'")

                response.raise_for_status()
                return CatalogProductOut.model_validate(response.json())

            except CatalogProductNotFound:
                raise

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code

                # Reintentar solo errores del servidor (5xx).
                if status < 500 or attempt >= self.max_retries:
                    raise

                await self._wait_before_retry(attempt, url, f"HTTP {status}")

            except httpx.RequestError as exc:
                # Incluye timeouts y fallos de conexión.
                if attempt >= self.max_retries:
                    raise CatalogRequestError(
                        f"Falló la solicitud para '{product_id}' "
                        f"después de {attempt + 1} intentos"
                    ) from exc

                await self._wait_before_retry(attempt, url, str(exc))

        raise CatalogRequestError(f"No se pudo obtener '{product_id}'")

    async def download_file(self, url: str, destination: Path) -> Path:
        """Descarga la respuesta por bloques y la guarda en disco.

        Escribe primero en un archivo .part y lo renombra al finalizar.
        Si la descarga falla, elimina el archivo temporal.
        """
        temporary_path = destination.with_name(destination.name + ".part")
        destination.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(self.max_retries + 1):
            try:
                async with self._client.stream("GET", url) as response:
                    if response.status_code == 404:
                        raise CatalogProductNotFound(f"No se encontró el recurso '{url}'")

                    response.raise_for_status()

                    with temporary_path.open("wb") as output_file:
                        async for chunk in response.aiter_bytes():
                            output_file.write(chunk)

                temporary_path.replace(destination)
                logger.info("Descarga guardada en %s", destination)
                return destination

            except CatalogProductNotFound:
                temporary_path.unlink(missing_ok=True)
                raise

            except httpx.HTTPStatusError as exc:
                temporary_path.unlink(missing_ok=True)
                status = exc.response.status_code

                if status < 500 or attempt >= self.max_retries:
                    raise

                await self._wait_before_retry(attempt, url, f"HTTP {status}")

            except httpx.RequestError as exc:
                temporary_path.unlink(missing_ok=True)

                if attempt >= self.max_retries:
                    raise CatalogRequestError(
                        f"Falló la descarga de '{url}' " f"después de {attempt + 1} intentos"
                    ) from exc

                await self._wait_before_retry(attempt, url, str(exc))

        raise CatalogRequestError(f"No se pudo descargar '{url}'")

    async def _wait_before_retry(
        self,
        attempt: int,
        url: str,
        reason: str,
    ) -> None:
        """Aplica espera exponencial antes del siguiente intento."""
        delay = self.backoff_factor * (2**attempt)
        logger.warning(
            "Solicitud a %s falló (%s). Reintento en %.2f s",
            url,
            reason,
            delay,
        )
        await asyncio.sleep(delay)
