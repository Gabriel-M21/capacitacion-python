"""
Demo del Módulo 11: Concurrencia y rendimiento
Demuestra:
  1. Fetcher SÍNCRONO vs ASÍNCRONO con semáforo (httpx + asyncio)
  2. Cálculo CPU-bound SECUENCIAL vs ProcessPoolExecutor
  3. Tabla comparativa de tiempos y speedup
Reutiliza: CatalogClient (Módulo 7), volume_discount (Módulo 10),
           orders.json (Módulo 6)
"""

import asyncio
import json
import logging
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from pathlib import Path

import httpx

from order_management.clients.catalog_client import (
    CatalogClient,
    CatalogProductNotFound,
)
from order_management.domain.pricing import volume_discount

logging.basicConfig(
    level=logging.WARNING,          # silenciamos INFO para ver solo la demo
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SMOCKER_URL  = "http://localhost:8080"
ORDERS_PATH  = Path("data") / "orders.json"
MAX_WORKERS  = multiprocessing.cpu_count()
SEMAPHORE    = 10          # máximo de peticiones HTTP simultáneas


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def load_product_names(path: Path) -> list[str]:
    """Extrae nombres de producto únicos y válidos desde orders.json."""
    orders = json.loads(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for order in orders:
        for item in order.get("items", []):
            name = item.get("product_name", "").strip()
            price = item.get("price", 0)
            if name and float(price) > 0:
                names.add(name)
    return sorted(names)


def load_orders_items(path: Path) -> list[dict]:
    """Extrae todos los items válidos para el cálculo CPU-bound."""
    orders = json.loads(path.read_text(encoding="utf-8"))
    items = []
    for order in orders:
        order_items = [
            i for i in order.get("items", [])
            if i.get("product_name", "").strip() and float(i.get("price", 0)) > 0
        ]
        if order_items:
            items.append({
                "order_id": order.get("order_id"),
                "item_count": len(order_items),
                "total": sum(float(i["price"]) * i.get("quantity", 1)
                             for i in order_items),
            })
    return items


# ---------------------------------------------------------------------------
# PARTE 1A — Fetcher SÍNCRONO (baseline)
# ---------------------------------------------------------------------------

def fetch_sync(product_names: list[str]) -> list[dict]:
    """
    Consulta el catálogo de forma síncrona, una petición a la vez.
    Usa httpx.Client (síncrono) directamente.
    """
    results = []
    with httpx.Client(base_url=SMOCKER_URL, timeout=5.0) as client:
        for name in product_names:
            from urllib.parse import quote
            try:
                response = client.get(f"/products/{quote(name, safe='')}")
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        "product_name": name,
                        "unit_price": data.get("unit_price"),
                        "available": data.get("available"),
                    })
            except httpx.RequestError:
                logger.warning("Error al consultar '%s'", name)
    return results


# ---------------------------------------------------------------------------
# PARTE 1B — Fetcher ASÍNCRONO con semáforo
# ---------------------------------------------------------------------------

async def fetch_one(
    client: CatalogClient,
    name: str,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Consulta un producto respetando el semáforo de concurrencia."""
    async with semaphore:
        try:
            product = await client.get_product(name)
            return {
                "product_name": name,
                "unit_price": str(product.unit_price),
                "available": product.available,
            }
        except CatalogProductNotFound:
            return None
        except httpx.RequestError as exc:
            logger.warning("Error al consultar '%s': %s", name, exc)
            return None


async def fetch_async(product_names: list[str]) -> list[dict]:
    """
    Consulta todos los productos concurrentemente,
    limitando a SEMAPHORE peticiones simultáneas.
    """
    semaphore = asyncio.Semaphore(SEMAPHORE)
    async with CatalogClient(
        base_url=SMOCKER_URL,
        timeout=5.0,
        max_retries=1,
        backoff_factor=0.1,
    ) as client:
        tasks = [
            fetch_one(client, name, semaphore)
            for name in product_names
        ]
        results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# PARTE 2A — Cálculo CPU-bound SECUENCIAL
# ---------------------------------------------------------------------------

def compute_discount_for_order(order: dict) -> dict:
    """
    Calcula el descuento y el ahorro para una orden.
    Esta función se ejecuta en un proceso separado (debe ser picklable).
    """
    item_count = order["item_count"]
    total      = Decimal(str(order["total"]))
    discount_pct = volume_discount(item_count)
    factor       = (Decimal("100") - discount_pct) / Decimal("100")
    final        = total * factor
    saving       = total - final
    return {
        "order_id":     order["order_id"],
        "item_count":   item_count,
        "total":        float(total),
        "discount_pct": float(discount_pct),
        "final":        float(final),
        "saving":       float(saving),
    }


def compute_sequential(orders: list[dict]) -> list[dict]:
    """Procesa todas las órdenes en un solo proceso."""
    return [compute_discount_for_order(o) for o in orders]


# ---------------------------------------------------------------------------
# PARTE 2B — Cálculo CPU-bound con ProcessPoolExecutor
# ---------------------------------------------------------------------------

def compute_parallel(orders: list[dict]) -> list[dict]:
    """
    Distribuye el cálculo entre MAX_WORKERS procesos.
    Cada proceso recibe un subconjunto de órdenes (chunks).
    """
    chunk_size = max(1, len(orders) // MAX_WORKERS)
    chunks = [
        orders[i: i + chunk_size]
        for i in range(0, len(orders), chunk_size)
    ]

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(compute_sequential, chunk) for chunk in chunks]
        for future in futures:
            results.extend(future.result())
    return results


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("MÓDULO 11: CONCURRENCIA Y RENDIMIENTO")
    print("asyncio · semáforo · ProcessPoolExecutor · timeit")
    print("=" * 70)

    product_names = load_product_names(ORDERS_PATH)
    orders        = load_orders_items(ORDERS_PATH)

    print(f"\n  Productos únicos a consultar : {len(product_names)}")
    print(f"  Órdenes a procesar           : {len(orders)}")
    print(f"  CPUs disponibles             : {MAX_WORKERS}")
    print(f"  Semáforo HTTP                : {SEMAPHORE} peticiones simultáneas")

    # ── PARTE 1: HTTP ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PARTE 1 — FETCHER HTTP: SÍNCRONO vs ASÍNCRONO")
    print("=" * 70)

    # 1A — Síncrono
    print(f"\n▶ Versión síncrona ({len(product_names)} productos, 1 a 1)...")
    t0 = time.perf_counter()
    sync_results = fetch_sync(product_names)
    sync_time = time.perf_counter() - t0
    print(f"  Productos obtenidos : {len(sync_results)}")
    print(f"  Tiempo              : {sync_time:.3f} s")

    # 1B — Asíncrono con semáforo
    print(f"\n▶ Versión asíncrona (semáforo={SEMAPHORE})...")
    t0 = time.perf_counter()
    async_results = asyncio.run(fetch_async(product_names))
    async_time = time.perf_counter() - t0
    speedup_http = sync_time / async_time if async_time > 0 else 0
    print(f"  Productos obtenidos : {len(async_results)}")
    print(f"  Tiempo              : {async_time:.3f} s")
    print(f"  Speedup             : {speedup_http:.1f}x más rápido")

    # Muestra primeros 5 productos obtenidos
    print("\n  Muestra (primeros 5 productos):")
    print(f"  {'Producto':<35} {'Precio':>8}  Disponible")
    print("  " + "-" * 55)
    for r in async_results[:5]:
        avail = "✓" if r["available"] else "✗"
        print(f"  {r['product_name'][:34]:<35} ${r['unit_price']:>7}  {avail}")

    # ── PARTE 2: CPU-bound ─────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PARTE 2 — CPU-BOUND: SECUENCIAL vs ProcessPoolExecutor")
    print("=" * 70)

    # Multiplicamos las órdenes para hacer el cálculo más visible
    orders_large = orders * 1000
    print(f"\n  Órdenes a procesar (x1000) : {len(orders_large)}")

    # 2A — Secuencial
    print("\n▶ Versión secuencial (1 proceso)...")
    t0 = time.perf_counter()
    seq_results = compute_sequential(orders_large)
    seq_time = time.perf_counter() - t0
    print(f"  Órdenes procesadas : {len(seq_results)}")
    print(f"  Tiempo             : {seq_time:.3f} s")

    # 2B — Paralelo
    print(f"\n▶ Versión paralela ({MAX_WORKERS} procesos)...")
    t0 = time.perf_counter()
    par_results = compute_parallel(orders_large)
    par_time = time.perf_counter() - t0
    speedup_cpu = seq_time / par_time if par_time > 0 else 0
    print(f"  Órdenes procesadas : {len(par_results)}")
    print(f"  Tiempo             : {par_time:.3f} s")
    print(f"  Speedup            : {speedup_cpu:.1f}x más rápido")

    # Muestra primeros 5 descuentos calculados
    print("\n  Muestra (primeras 5 órdenes):")
    print(f"  {'Orden':<14} {'Items':>5} {'Total':>9} {'Desc%':>6} {'Final':>9} {'Ahorro':>9}")
    print("  " + "-" * 60)
    for r in par_results[:5]:
        print(
            f"  {r['order_id']:<14} "
            f"{r['item_count']:>5} "
            f"${r['total']:>8.2f} "
            f"{r['discount_pct']:>5.0f}% "
            f"${r['final']:>8.2f} "
            f"${r['saving']:>8.2f}"
        )

    # ── TABLA COMPARATIVA ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN COMPARATIVO")
    print("=" * 70)
    print(f"\n  {'Estrategia':<35} {'Tiempo':>8}  {'Speedup':>8}")
    print("  " + "-" * 55)
    print(f"  {'HTTP síncrono':<35} {sync_time:>7.3f}s  {'1.0x':>8}")
    print(f"  {'HTTP asíncrono (semáforo=10)':<35} {async_time:>7.3f}s  {speedup_http:>7.1f}x")
    print(f"  {'CPU secuencial (1 proceso)':<35} {seq_time:>7.3f}s  {'1.0x':>8}")
    print(f"  {'CPU paralelo ({} procesos)':<35} {par_time:>7.3f}s  {speedup_cpu:>7.1f}x".format(MAX_WORKERS))

    # ── GIL — nota educativa ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("NOTA: EL GIL Y CUÁNDO IMPORTA")
    print("=" * 70)
    print("""
  • asyncio (I/O-bound)      → el GIL no es problema: mientras una
    corrutina espera la respuesta HTTP, otras corrutinas corren.
    Por eso el fetcher asíncrono es mucho más rápido.

  • threading (I/O-bound)    → similar a asyncio pero con overhead
    de cambio de contexto entre hilos. Válido pero asyncio es preferible.

  • ProcessPoolExecutor       → cada proceso tiene su propio GIL,
    por lo que el trabajo CPU-bound se distribuye de verdad entre núcleos.
    Por eso el cálculo paralelo supera al secuencial.

  • threading (CPU-bound)    → el GIL impide paralelismo real;
    los hilos se turnan, no corren simultáneamente. Evitar para CPU-bound.
    """)

    print("=" * 70)
    print("✓ DEMO MÓDULO 11 COMPLETADO")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
