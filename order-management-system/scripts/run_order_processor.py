"""
Script de ejemplo para ejecutar el procesador de órdenes.
Demuestra todos los conceptos del Módulo 2.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from order_management.core.order_processor import OrderProcessor  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"


def main() -> None:
    """Función principal del script"""
    print("=" * 60)
    print("PROCESADOR DE ÓRDENES - Módulo 2: Fundamentos")
    print("=" * 60)

    # Crear procesador
    processor = OrderProcessor()

    # Ruta al archivo JSON
    data_file = DATA_DIR / "orders_sample.json"
    try:
        # 1. Cargar órdenes desde JSON
        print(f"\nCargando órdenes desde: {data_file}")
        orders = processor.load_orders_from_json(data_file)
        print(f"Se cargaron {len(orders)} órdenes del archivo")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Asegúrate de tener el archivo data/orders_sample.json")
        return
    except ValueError as e:
        print(f"Error de validación: {e}")
        return
    except Exception as e:
        print(f"Error inesperado: {e}")
        return

    # 2. Procesar órdenes
    print("\nProcesando órdenes...")
    try:
        stats = processor.process_orders(orders, skip_invalid=True)

        print("\nESTADÍSTICAS GENERALES:")
        print(f"   Total órdenes procesadas: {stats['valid_orders']}")
        print(f"   Órdenes inválidas: {stats['invalid_orders']}")
        print(f"   Revenue total: ${stats['total_revenue']:,.2f}")
        print(f"   Valor promedio por orden: ${stats['average_order_value']:,.2f}")
        print(f"   Clientes únicos: {stats['unique_customers']}")

        print("\nÓRDENES POR ESTADO:")
        for status, count in stats["orders_by_status"].items():
            print(f"   {status}: {count}")

        if stats["invalid_details"]:
            print("\nÓRDENES INVÁLIDAS:")
            for invalid in stats["invalid_details"]:
                print(f"   - Índice {invalid['index']}: {invalid['error']}")

    except ValueError as e:
        print(f"Error al procesar: {e}")
        return

    # 3. Filtrar órdenes por estado (solo válidas)
    print("\nFILTRADO POR ESTADO 'confirmed' (solo válidas):")
    confirmed_orders = processor.filter_orders_by_status(processor.processed_orders, "confirmed")
    print(f"   Encontradas: {len(confirmed_orders)} órdenes")
    for order in confirmed_orders:
        print(f"   - {order['order_id']}: {order['customer_name']}")

    # 4. Filtrar por total mínimo
    min_total = 100.0
    print(f"\nÓRDENES CON TOTAL >= ${min_total}:")
    high_value_orders = processor.filter_orders_by_min_total(processor.processed_orders, min_total)
    for order in high_value_orders:
        print(f"   - {order['order_id']}: ${order['total']:,.2f} ({order['category']})")

    # 5. Top clientes
    print("\nTOP 3 CLIENTES:")
    top_customers = processor.get_top_customers(top_n=3)
    for idx, (customer, total) in enumerate(top_customers, 1):
        print(f"   {idx}. {customer}: ${total:,.2f}")

    # 6. Categorización por total (pattern matching)
    print("\nCATEGORIZACIÓN DE ÓRDENES:")
    test_totals = [0, 25.50, 75.00, 250.00, 1500.00]
    for total in test_totals:
        category = processor.categorize_order_by_total(total)
        print(f"   Total ${total}: {category}")

    # 7. Exportar resumen
    output_file = DATA_DIR / "orders_summary.json"
    print(f"\nExportando resumen a: {output_file}")
    try:
        processor.export_summary_to_json(output_file, stats)
        print("Resumen exportado exitosamente")
    except OSError as e:
        print(f"Error al exportar: {e}")

    print("\n" + "=" * 60)
    print("Procesamiento completado")
    print("=" * 60)


if __name__ == "__main__":
    main()
