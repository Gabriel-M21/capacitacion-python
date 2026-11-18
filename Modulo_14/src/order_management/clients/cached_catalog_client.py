"""
Cliente de catálogo con caché - Módulo 13: Patrones de diseño
Patrón: Decorator

Envuelve CatalogClient añadiendo caché en memoria transparente.
El cliente original no se modifica — el Decorator añade comportamiento
sin herencia, solo composición.
"""

import logging
from typing import Any, cast

from order_management.schemas.schemas import CatalogProductOut

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol del cliente original (para type safety)
# ---------------------------------------------------------------------------


class CatalogClientProtocol:
    """Interfaz mínima que el Decorator espera del cliente envuelto."""

    async def get_product(self, product_id: str) -> CatalogProductOut:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Decorator — añade caché sin modificar CatalogClient
# ---------------------------------------------------------------------------


class CachedCatalogClient:
    """
    Decorator de CatalogClient que almacena respuestas en memoria.

    Decorator: añade responsabilidades a un objeto dinámicamente,
    sin modificar su clase ni usar herencia.

    Transparente para el consumidor: tiene la misma interfaz que
    CatalogClient (get_product), por lo que es completamente
    intercambiable (LSP).

    Example:
        real_client  = CatalogClient(base_url="http://localhost:8080")
        cached_client = CachedCatalogClient(client=real_client, ttl=300)
        product = await cached_client.get_product("Laptop Dell XPS 15")
        # Segunda llamada: devuelve desde caché sin hit HTTP
        product = await cached_client.get_product("Laptop Dell XPS 15")
    """

    def __init__(
        self,
        client: Any,
        ttl: int = 300,
        max_size: int = 200,
    ) -> None:
        """
        Args:
            client:   Cliente real a decorar (CatalogClient)
            ttl:      Time-to-live en segundos (no implementado en demo,
                      presente para ilustrar configuración real)
            max_size: Número máximo de productos en caché
        """
        self._client = client
        self._ttl = ttl
        self._max_size = max_size
        self._cache: dict[str, CatalogProductOut] = {}
        self._hits: int = 0
        self._misses: int = 0

    # ------------------------------------------------------------------
    # Interfaz decorada
    # ------------------------------------------------------------------

    async def get_product(self, product_id: str) -> CatalogProductOut:
        """
        Devuelve el producto desde caché si está disponible;
        si no, delega al cliente real y almacena el resultado.
        """
        if product_id in self._cache:
            self._hits += 1
            logger.debug("CACHE HIT  → '%s' (%d hits)", product_id, self._hits)
            return self._cache[product_id]

        # Cache miss: consultar al cliente real
        self._misses += 1
        logger.debug("CACHE MISS → '%s' (%d misses)", product_id, self._misses)

        product: CatalogProductOut = cast(
            CatalogProductOut,
            await self._client.get_product(product_id),
        )

        # Evict si el caché está lleno (política LRU simplificada: elimina el primero)
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug("CACHE EVICT → '%s'", oldest_key)

        self._cache[product_id] = product
        return product

    # ------------------------------------------------------------------
    # Delegación de otros métodos al cliente original
    # ------------------------------------------------------------------

    async def download_file(self, url: str, destination: Any) -> Any:
        """Delega download_file al cliente real sin caché."""
        return await self._client.download_file(url, destination)

    async def __aenter__(self) -> "CachedCatalogClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)

    # ------------------------------------------------------------------
    # Métricas del caché
    # ------------------------------------------------------------------

    @property
    def cache_size(self) -> int:
        """Número de productos actualmente en caché."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos (0.0 - 1.0)."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict[str, Any]:
        """Resumen de estadísticas del caché."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
            "cache_size": self.cache_size,
        }

    def invalidate(self, product_id: str | None = None) -> None:
        """
        Invalida una entrada específica o todo el caché.

        Args:
            product_id: Si se provee, invalida solo ese producto.
                        Si es None, vacía todo el caché.
        """
        if product_id is not None:
            self._cache.pop(product_id, None)
        else:
            self._cache.clear()
            logger.debug("CACHE CLEARED")
