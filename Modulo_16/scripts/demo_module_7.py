"""
Demo del Módulo 7: HTTP y consumo de APIs con Smocker
- Lee orders.json (Módulo 6)
- Consulta el catálogo simulado con httpx (Módulo 7)
- Compara precios orden vs catálogo
- Descarga el catálogo completo por streaming
"""

import asyncio
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import cast

import httpx
from pydantic import ValidationError

from order_management.clients.catalog_client import CatalogClient, CatalogProductNotFound
from order_management.schemas.schemas import CatalogProductOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SMOCKER_URL = "http://localhost:8080"
ORDERS_PATH = Path("data") / "orders.json"
DOWNLOAD_DEST = Path("data") / "output" / "catalog_download.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_orders(path: Path) -> list[dict]:
    """Lee y parsea orders.json."""
    logger.info("Leyendo órdenes desde %s", path)
    return cast(list[dict], json.loads(path.read_text(encoding="utf-8")))


def extract_valid_items(orders: list[dict]) -> list[dict]:
    """Extrae items con product_name y price válidos."""
    items = []
    for order in orders:
        order_id = order.get("order_id", "?")
        for item in order.get("items", []):
            name = item.get("product_name", "").strip()
            price = item.get("price")
            if name and price and float(price) > 0:
                items.append(
                    {
                        "order_id": order_id,
                        "product_name": name,
                        "order_price": Decimal(str(price)),
                    }
                )
    return items


def price_diff_label(order_price: Decimal, catalog_price: Decimal) -> str:
    """Devuelve una etiqueta comparando el precio de la orden con el catálogo."""
    diff = catalog_price - order_price
    if diff > 0:
        return f"↑ catálogo más caro  (+${diff:.2f})"
    elif diff < 0:
        return f"↓ catálogo más barato (-${abs(diff):.2f})"
    else:
        return "= precio igual"


# ---------------------------------------------------------------------------
# Consulta al catálogo
# ---------------------------------------------------------------------------


async def fetch_catalog_products(
    client: CatalogClient,
    items: list[dict],
) -> list[dict]:
    """
    Consulta el catálogo para cada product_name único.
    Retorna una lista con la comparación de precios.
    """
    seen: dict[str, CatalogProductOut] = {}
    results = []

    for item in items:
        name = item["product_name"]

        if name not in seen:
            try:
                product = await client.get_product(name)
                seen[name] = product
            except CatalogProductNotFound:
                logger.warning("Producto no encontrado en catálogo: '%s'", name)
                continue
            except (httpx.RequestError, ValidationError) as exc:
                logger.error("Error al consultar '%s': %s", name, exc)
                continue

        catalog = seen[name]
        results.append(
            {
                "order_id": item["order_id"],
                "product_name": name,
                "order_price": item["order_price"],
                "catalog_price": catalog.unit_price,
                "available": catalog.available,
                "diff": price_diff_label(item["order_price"], catalog.unit_price),
            }
        )

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    print("\n" + "=" * 70)
    print("MÓDULO 7: HTTP Y CONSUMO DE APIs — SMOCKER")
    print("=" * 70)

    # 1. Leer órdenes
    orders = load_orders(ORDERS_PATH)
    items = extract_valid_items(orders)
    logger.info("Items válidos encontrados: %d", len(items))

    async with CatalogClient(
        base_url=SMOCKER_URL,
        timeout=5.0,
        max_retries=2,
        backoff_factor=0.3,
    ) as client:

        # 2. Consultar catálogo por cada item
        print("\n" + "=" * 70)
        print("1. CONSULTA DE PRODUCTOS AL CATÁLOGO")
        print("=" * 70)

        results = await fetch_catalog_products(client, items)

        # Mostrar comparación
        print(f"\n{'Orden':<14} {'Producto':<35} {'Orden':>8} {'Catálogo':>9}  Diferencia")
        print("-" * 90)
        for r in results:
            avail = "✓" if r["available"] else "✗"
            print(
                f"{r['order_id']:<14} "
                f"{r['product_name'][:34]:<35} "
                f"${r['order_price']:>7.2f} "
                f"${r['catalog_price']:>8.2f}  "
                f"{avail} {r['diff']}"
            )

        # Resumen
        print("\n" + "=" * 70)
        print("2. RESUMEN")
        print("=" * 70)
        total_consultados = len(results)
        precio_igual = sum(1 for r in results if r["order_price"] == r["catalog_price"])
        precio_diferente = total_consultados - precio_igual
        no_disponibles = sum(1 for r in results if not r["available"])

        print(f"\n  Productos consultados : {total_consultados}")
        print(f"  Precio coincide       : {precio_igual}")
        print(f"  Precio difiere        : {precio_diferente}")
        print(f"  No disponibles        : {no_disponibles}")

        # 3. Descarga por streaming
        print("\n" + "=" * 70)
        print("3. DESCARGA POR STREAMING")
        print("=" * 70)

        try:
            downloaded = await client.download_file(
                "/exports/catalog.json",
                DOWNLOAD_DEST,
            )
            size = downloaded.stat().st_size
            print(f"\n  ✓ Archivo guardado en : {downloaded.resolve()}")
            print(f"  ✓ Tamaño              : {size} bytes")
            print("\n  Contenido:")
            content = json.loads(downloaded.read_text(encoding="utf-8"))
            print(f"  {json.dumps(content, indent=2, ensure_ascii=False)[:300]}...")
        except Exception as exc:
            logger.error("Error en descarga: %s", exc)

    print("\n" + "=" * 70)
    print("✓ DEMO MÓDULO 7 COMPLETADO")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
