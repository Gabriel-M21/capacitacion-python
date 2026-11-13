"""
Script Módulo 3: Demostración de utilidades pythonic
Procesa órdenes con OrderProcessor y luego aplica utilidades pythonic
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from order_management.core.order_processor import OrderProcessor  # noqa: E402
from order_management.utils.context_managers import Timer  # noqa: E402
from order_management.utils.decorators import create_discount_calculator  # noqa: E402
from order_management.utils.generators import batch_processor, get_order_summaries  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"


def main() -> None:
    print("=" * 70)
    print("DEMO MÓDULO 3: Utilidades Pythonic")
    print("=" * 70)

    # PASO 1: Procesar órdenes con Módulo 2
    print("\n[PASO 1] Procesando órdenes con OrderProcessor (Módulo 2)...")
    processor = OrderProcessor()

    with Timer("Carga y procesamiento"):
        data_file = DATA_DIR / "orders_sample.json"
        orders = processor.load_orders_from_json(data_file)
        stats = processor.process_orders(orders, skip_invalid=True)

    print(f"✓ Procesadas: {stats['valid_orders']} órdenes")
    print(f"✓ Revenue: ${stats['total_revenue']:,.2f}")

    # PASO 2: Aplicar utilidades pythonic del Módulo 3
    print("\n[PASO 2] Aplicando utilidades pythonic (Módulo 3)...")

    # Obtener órdenes procesadas (con totales calculados)
    processed = processor.processed_orders

    # Generador de lotes
    print("\na) Procesamiento por lotes:")
    batch_count = 0
    for batch in batch_processor(processed, batch_size=3):
        batch_count += 1
        batch_total = sum(o["total"] for o in batch)
        print(f"   Lote {batch_count}: {len(batch)} órdenes, Total: ${batch_total:.2f}")

    # Comprensiones
    print("\nb) Resúmenes con comprensiones:")
    summaries = get_order_summaries(processed)
    print(f"   Revenue total: ${summaries['total_revenue']:.2f}")
    print(f"   Órdenes > $100: {summaries['high_value_count']}")
    print(f"   Clientes únicos: {len(summaries['unique_customers'])}")

    # Closures con descuentos
    print("\nc) Aplicar descuentos con closures:")
    black_friday = create_discount_calculator(50)

    for order in processed[:3]:
        original = order["total"]
        discounted = black_friday(original)
        print(
            f"   {order['order_id']}: ${original:.2f} → ${discounted:.2f} "
            f"(ahorro: ${original - discounted:.2f})"
        )

    # Lambdas
    print("\nd) Top 3 órdenes con lambdas:")
    top_orders = sorted(processed, key=lambda o: o["total"], reverse=True)[:3]
    for idx, order in enumerate(top_orders, 1):
        print(f"   {idx}. {order['order_id']}: ${order['total']:.2f}")

    print("\n" + "=" * 70)
    print("✓ DEMO MÓDULO 3 COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
