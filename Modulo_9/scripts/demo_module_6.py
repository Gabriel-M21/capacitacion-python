"""
Script de laboratorio - Módulo 6: Librería estándar y E/S
Demuestra: pathlib, csv, json, datetime, logging, subprocess
Basado en las clases existentes de order_management
"""

import csv
import json
import logging
import logging.config
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from order_management.domain.entities import Order
from order_management.domain.value_objects import OrderId, OrderStatus
from order_management.mappers.order_mapper import OrderMapper
from order_management.schemas.schemas import CustomerIn, OrderIn, OrderItemIn

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LOGGING ESTRUCTURADO
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": LOG_FORMAT, "datefmt": DATE_FORMAT},
            "detailed": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
                "datefmt": DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": "orders_lab.log",
                "mode": "w",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "lab.ingestion": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
            "lab.metrics": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
            "lab.export": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        },
    }
)

ingestion_log = logging.getLogger("lab.ingestion")
metrics_log = logging.getLogger("lab.metrics")
export_log = logging.getLogger("lab.export")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

VALID_STATUSES = {s.value for s in OrderStatus}


def _parse_status(raw: str) -> OrderStatus:
    """Convierte string a OrderStatus."""
    mapping = {
        "pending": OrderStatus.PENDING,
        "confirmed": OrderStatus.CONFIRMED,
        "shipped": OrderStatus.SHIPPED,
        "delivered": OrderStatus.DELIVERED,
        "cancelled": OrderStatus.CANCELLED,
    }
    key = raw.strip().lower()
    if key not in mapping:
        raise ValueError(f"Estado desconocido: '{raw}'")
    return mapping[key]


def _parse_datetime(raw: str) -> datetime:
    """Parsea string ISO a datetime con timezone UTC."""
    # Acepta '2024-01-10T09:15:00' y '2024-01-10 09:15:00'
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: '{raw}'")


# ---------------------------------------------------------------------------
# 2. INGESTA DESDE CSV
# ---------------------------------------------------------------------------


def ingest_from_csv(csv_path: Path) -> tuple[list[Order], list[dict[str, Any]]]:
    """
    Lee orders.csv y construye objetos Order del dominio.

    El CSV tiene una fila por item; se agrupan por order_id.

    Args:
        csv_path: Ruta al archivo CSV

    Returns:
        Tupla (órdenes válidas, registros de errores)
    """
    ingestion_log.info("=== INGESTA CSV ===")
    ingestion_log.info(f"Leyendo archivo: {csv_path.resolve()}")

    if not csv_path.exists():
        ingestion_log.error(f"Archivo no encontrado: {csv_path}")
        raise FileNotFoundError(csv_path)

    # Agrupamos filas por order_id antes de construir objetos
    raw_orders: dict[str, dict[str, Any]] = {}

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row_num, row in enumerate(reader, start=2):  # 2 porque la fila 1 es el header
            oid = row.get("order_id", "").strip()
            if not oid:
                ingestion_log.warning(f"Fila {row_num}: order_id vacío, se omite")
                continue

            if oid not in raw_orders:
                raw_orders[oid] = {
                    "order_id": oid,
                    "customer_name": row.get("customer_name", "").strip(),
                    "email": row.get("email", "").strip(),
                    "status": row.get("status", "").strip(),
                    "created_at": row.get("created_at", "").strip(),
                    "items": [],
                }

            product_name = row.get("product_name", "").strip()
            quantity_raw = row.get("quantity", "").strip()
            price_raw = row.get("price", "").strip()

            if product_name and quantity_raw and price_raw:
                raw_orders[oid]["items"].append(
                    {
                        "product_name": product_name,
                        "quantity": quantity_raw,
                        "price": price_raw,
                    }
                )

    ingestion_log.debug(f"Grupos encontrados: {len(raw_orders)}")

    valid_orders: list[Order] = []
    errors: list[dict[str, Any]] = []

    for idx, (oid, data) in enumerate(raw_orders.items(), start=1):
        ingestion_log.debug(f"Procesando {oid} ({idx}/{len(raw_orders)})")
        try:
            order = _build_order_from_raw(data, source="CSV")
            valid_orders.append(order)
            ingestion_log.info(f"✓ {oid} - {order.customer.name} - total: {order.total}")
        except Exception as exc:
            ingestion_log.warning(f"✗ {oid} inválida: {exc}")
            errors.append({"order_id": oid, "source": "CSV", "error": str(exc), "data": data})

    ingestion_log.info(f"CSV completado — válidas: {len(valid_orders)}, errores: {len(errors)}")
    return valid_orders, errors


# ---------------------------------------------------------------------------
# 3. INGESTA DESDE JSON
# ---------------------------------------------------------------------------


def ingest_from_json(json_path: Path) -> tuple[list[Order], list[dict[str, Any]]]:
    """
    Lee orders.json y construye objetos Order del dominio.

    Args:
        json_path: Ruta al archivo JSON

    Returns:
        Tupla (órdenes válidas, registros de errores)
    """
    ingestion_log.info("=== INGESTA JSON ===")
    ingestion_log.info(f"Leyendo archivo: {json_path.resolve()}")

    if not json_path.exists():
        ingestion_log.error(f"Archivo no encontrado: {json_path}")
        raise FileNotFoundError(json_path)

    raw_data: list[dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    ingestion_log.debug(f"Registros encontrados: {len(raw_data)}")

    valid_orders: list[Order] = []
    errors: list[dict[str, Any]] = []

    for idx, record in enumerate(raw_data, start=1):
        oid = record.get("order_id", f"<sin_id_{idx}>")
        ingestion_log.debug(f"Procesando {oid} ({idx}/{len(raw_data)})")

        # Normalizar estructura JSON → misma forma que CSV raw
        raw = {
            "order_id": oid,
            "customer_name": record.get("customer_name", ""),
            "email": record.get("email", ""),
            "status": record.get("status", ""),
            "created_at": record.get("created_at", ""),
            "items": [
                {
                    "product_name": it.get("product_name", ""),
                    "quantity": str(it.get("quantity", "")),
                    "price": str(it.get("price", "")),
                }
                for it in record.get("items", [])
            ],
        }

        try:
            order = _build_order_from_raw(raw, source="JSON")
            valid_orders.append(order)
            ingestion_log.info(f"✓ {oid} - {order.customer.name} - total: {order.total}")
        except Exception as exc:
            ingestion_log.warning(f"✗ {oid} inválida: {exc}")
            errors.append({"order_id": oid, "source": "JSON", "error": str(exc), "data": raw})

    ingestion_log.info(f"JSON completado — válidas: {len(valid_orders)}, errores: {len(errors)}")
    return valid_orders, errors


# ---------------------------------------------------------------------------
# BUILDER COMPARTIDO
# ---------------------------------------------------------------------------


def _build_order_from_raw(data: dict[str, Any], source: str = "") -> Order:
    """
    Construye un objeto Order de dominio a partir de un dict normalizado.

    Valida usando OrderIn (Pydantic) y luego convierte con OrderMapper.

    Args:
        data: Dict con keys: order_id, customer_name, email, status, items
        source: Etiqueta de origen para logging

    Returns:
        Order de dominio validado

    Raises:
        ValueError: Si algún campo es inválido
    """
    # 1. Validaciones básicas previas a Pydantic
    customer_name = data.get("customer_name", "").strip()
    if not customer_name:
        raise ValueError("customer_name vacío")

    email_raw = data.get("email", "").strip()
    if not email_raw:
        raise ValueError("email ausente")

    status_raw = data.get("status", "").strip()
    if not status_raw:
        raise ValueError("status ausente")

    raw_items = data.get("items", [])
    if not raw_items:
        raise ValueError("sin items")

    # 2. Parsear items
    parsed_items: list[dict[str, Any]] = []
    for it in raw_items:
        product_name = str(it.get("product_name", "")).strip()
        try:
            quantity = int(it["quantity"])
            price = Decimal(str(it["price"]))
        except (KeyError, ValueError, Exception) as e:
            raise ValueError(f"item '{product_name}' con datos inválidos: {e}") from e

        if quantity <= 0:
            raise ValueError(f"quantity <= 0 en item '{product_name}'")
        if price <= 0:
            raise ValueError(f"price <= 0 en item '{product_name}'")

        parsed_items.append(
            {"product_name": product_name, "quantity": quantity, "unit_price": price}
        )

    # 3. Validar con Pydantic (OrderIn)
    order_in = OrderIn(
        customer=CustomerIn(name=customer_name, email=email_raw, phone=None),
        items=[OrderItemIn(**it) for it in parsed_items],
        notes=None,
    )

    # 4. Parsear OrderId
    raw_id = data.get("order_id", "").strip()
    # Extraer número del ID (ej: "ORD-001" → 1)
    numeric_part = raw_id.replace("ORD-", "").lstrip("0") or "0"
    try:
        order_num = int(numeric_part)
    except ValueError:
        order_num = abs(hash(raw_id)) % 100_000

    order_id = OrderId.generate(order_num)

    # 5. Convertir a dominio con Mapper
    order = OrderMapper.to_domain_order(order_in, order_id)

    # 6. Aplicar status real (el mapper lo crea en PENDING por defecto)
    target_status = _parse_status(status_raw)
    # Avanzar el estado paso a paso según transiciones válidas
    transitions = [
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    ]
    for step in transitions:
        if order.status == target_status:
            break
        if order.status.can_transition_to(step):
            order.change_status(step)
            if order.status == target_status:
                break

    return order


# ---------------------------------------------------------------------------
# 4. CÁLCULO DE MÉTRICAS
# ---------------------------------------------------------------------------


def compute_metrics(orders: list[Order]) -> dict[str, Any]:
    """
    Calcula métricas agregadas sobre una lista de órdenes.

    Args:
        orders: Lista de órdenes válidas

    Returns:
        Diccionario con métricas
    """
    metrics_log.info("=== CALCULANDO MÉTRICAS ===")

    if not orders:
        metrics_log.warning("Lista de órdenes vacía")
        return {}

    # Totales por status
    by_status: dict[str, dict[str, Any]] = {}
    for order in orders:
        key = order.status.value
        if key not in by_status:
            by_status[key] = {"count": 0, "total_revenue": Decimal("0")}
        by_status[key]["count"] += 1
        by_status[key]["total_revenue"] += order.total.amount

    # Totales por cliente
    by_customer: dict[str, dict[str, Any]] = {}
    for order in orders:
        name = order.customer.name
        if name not in by_customer:
            by_customer[name] = {
                "email": str(order.customer.email),
                "order_count": 0,
                "total_spent": Decimal("0"),
            }
        by_customer[name]["order_count"] += 1
        by_customer[name]["total_spent"] += order.total.amount

    # Top 3 productos más vendidos (por cantidad)
    product_counts: dict[str, int] = {}
    for order in orders:
        for item in order.items:
            product_counts[item.product_name] = (
                product_counts.get(item.product_name, 0) + item.quantity
            )
    top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Orden más cara y más barata
    sorted_by_total = sorted(orders, key=lambda o: o.total.amount)
    cheapest = sorted_by_total[0]
    most_expensive = sorted_by_total[-1]

    # Revenue total
    total_revenue = sum((o.total.amount for o in orders), Decimal("0"))
    avg_order_value = total_revenue / len(orders)

    metrics = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_orders": len(orders),
        "total_revenue": float(total_revenue),
        "avg_order_value": float(avg_order_value),
        "by_status": {
            k: {"count": v["count"], "total_revenue": float(v["total_revenue"])}
            for k, v in by_status.items()
        },
        "by_customer": {
            k: {
                "email": v["email"],
                "order_count": v["order_count"],
                "total_spent": float(v["total_spent"]),
            }
            for k, v in sorted(by_customer.items(), key=lambda x: x[1]["total_spent"], reverse=True)
        },
        "top_3_products": [
            {"product_name": name, "total_quantity": qty} for name, qty in top_products
        ],
        "most_expensive_order": {
            "order_id": str(most_expensive.order_id),
            "customer": most_expensive.customer.name,
            "total": float(most_expensive.total.amount),
        },
        "cheapest_order": {
            "order_id": str(cheapest.order_id),
            "customer": cheapest.customer.name,
            "total": float(cheapest.total.amount),
        },
    }

    metrics_log.info(f"Total órdenes procesadas : {metrics['total_orders']}")
    metrics_log.info(f"Revenue total            : ${metrics['total_revenue']:.2f}")
    metrics_log.info(f"Ticket promedio          : ${metrics['avg_order_value']:.2f}")
    for status, data in cast(dict[str, dict[str, Any]], metrics["by_status"]).items():
        metrics_log.info(f"  [{status:10}] {data['count']} órdenes — ${data['total_revenue']:.2f}")

    return metrics


# ---------------------------------------------------------------------------
# 5. EXPORTACIÓN A JSON
# ---------------------------------------------------------------------------


def export_metrics_to_json(
    metrics: dict[str, Any],
    errors: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """
    Exporta métricas y errores de validación a un archivo JSON.

    Args:
        metrics: Diccionario de métricas calculadas
        errors: Lista de registros inválidos con su motivo
        output_path: Ruta de salida
    """
    export_log.info("=== EXPORTANDO RESULTADOS ===")

    output = {
        "metrics": metrics,
        "validation_errors": [
            {
                "order_id": e["order_id"],
                "source": e.get("source", ""),
                "error": e["error"],
            }
            for e in errors
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    export_log.info(f"Resultados exportados a: {output_path.resolve()}")
    export_log.info(f"  Métricas         : {len(metrics)} claves")
    export_log.info(f"  Errores incluidos: {len(errors)}")


# ---------------------------------------------------------------------------
# 6. PATHLIB — exploración de archivos de datos
# ---------------------------------------------------------------------------


def demo_pathlib(data_dir: Path) -> None:
    """
    Demuestra operaciones con pathlib sobre el directorio de datos.

    Args:
        data_dir: Directorio donde están los archivos de datos
    """
    ingestion_log.info("=== DEMO PATHLIB ===")

    print("\n" + "=" * 70)
    print("1. PATHLIB — Manejo de rutas y archivos")
    print("=" * 70)

    print(f"\na) Directorio de trabajo  : {Path.cwd()}")
    print(f"   Directorio de datos    : {data_dir.resolve()}")
    print(f"   ¿Existe?               : {data_dir.exists()}")

    # Listar archivos de datos
    data_files = list(data_dir.glob("orders.*"))
    print(f"\nb) Archivos encontrados ({len(data_files)}):")
    for f in data_files:
        size_kb = f.stat().st_size / 1024
        modified = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
        print(
            f"   {f.name:20} {size_kb:6.1f} KB  |  modificado: {modified.strftime('%Y-%m-%d %H:%M')}"
        )

    # Construcción de rutas
    print("\nc) Construcción de rutas:")
    output_dir = data_dir / "output"
    metrics_file = output_dir / "metrics.json"
    print(f"   output dir  : {output_dir}")
    print(f"   metrics file: {metrics_file}")
    print(f"   sufijo      : {metrics_file.suffix}")
    print(f"   stem        : {metrics_file.stem}")
    print(f"   parent      : {metrics_file.parent}")


# ---------------------------------------------------------------------------
# 7. DEMO DATETIME Y ZONAS HORARIAS
# ---------------------------------------------------------------------------


def demo_datetime(orders: list[Order]) -> None:
    """
    Demuestra operaciones con datetime usando las órdenes cargadas.

    Args:
        orders: Órdenes válidas cargadas
    """
    print("\n" + "=" * 70)
    print("2. DATETIME — Fechas y zonas horarias")
    print("=" * 70)

    now_utc = datetime.now(UTC)
    print(f"\na) Hora actual UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Parsear fechas de creación desde el JSON
    sample_dates = [
        "2024-01-10T09:15:00",
        "2024-02-08T16:00:00",
        "2024-01-31T09:00:00",
    ]
    print("\nb) Parseo de fechas ISO:")
    for raw in sample_dates:
        dt = _parse_datetime(raw)
        print(f"   {raw}  →  {dt.strftime('%d/%m/%Y %H:%M')} UTC")

    # Diferencia entre fechas
    start = _parse_datetime("2024-01-10T09:15:00")
    end = _parse_datetime("2024-02-08T16:00:00")
    delta = end - start
    print("\nc) Diferencia entre fechas:")
    print(f"   Desde: {start.strftime('%d/%m/%Y')}")
    print(f"   Hasta: {end.strftime('%d/%m/%Y')}")
    print(f"   Días transcurridos: {delta.days}")

    # Formateo
    print("\nd) Formateo de fecha:")
    print(f"   ISO 8601  : {now_utc.isoformat()}")
    print(f"   Legible   : {now_utc.strftime('%d de %B de %Y, %H:%M')}")
    print(f"   Timestamp : {now_utc.timestamp():.0f}")


# ---------------------------------------------------------------------------
# 8. DEMO SUBPROCESS
# ---------------------------------------------------------------------------


def demo_subprocess() -> None:
    """Demuestra uso básico de subprocess para automatización."""
    print("\n" + "=" * 70)
    print("3. SUBPROCESS — Automatización de comandos")
    print("=" * 70)

    # Comando multiplataforma: listar archivos de datos
    cmd = (
        ["dir", "data\\*.json", "data\\*.csv", "/b"]
        if sys.platform == "win32"
        else ["ls", "-lh", "--color=never", "data/"]
    )

    print(f"\na) Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    if result.returncode == 0:
        lines = result.stdout.strip().splitlines()[:8]
        for line in lines:
            print(f"   {line}")
    else:
        print(f"   Error (código {result.returncode}): {result.stderr[:100]}")

    # Python --version como ejemplo seguro multiplataforma
    py_result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    print("\nb) Versión de Python activa:")
    print(f"   {py_result.stdout.strip() or py_result.stderr.strip()}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    """Función principal del laboratorio."""
    print("\n" + "=" * 70)
    print("MÓDULO 6: LIBRERÍA ESTÁNDAR Y E/S")
    print("pathlib · csv · json · datetime · logging · subprocess")
    print("=" * 70)

    # Rutas de trabajo
    data_dir = Path("data")  # Ajusta a la carpeta donde pusiste los archivos
    csv_path = data_dir / "orders.csv"
    json_path = data_dir / "orders.json"
    output_path = data_dir / "output" / "metrics.json"

    # ── 1. PATHLIB ──────────────────────────────────────────────────────────
    demo_pathlib(data_dir)

    # ── 2. INGESTA CSV ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("4. INGESTA CSV")
    print("=" * 70)
    csv_orders, csv_errors = ingest_from_csv(csv_path)
    print(f"\n   Órdenes válidas : {len(csv_orders)}")
    print(f"   Errores         : {len(csv_errors)}")

    # ── 3. INGESTA JSON ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("5. INGESTA JSON")
    print("=" * 70)
    json_orders, json_errors = ingest_from_json(json_path)
    print(f"\n   Órdenes válidas : {len(json_orders)}")
    print(f"   Errores         : {len(json_errors)}")

    # Usar las del JSON (más completas: tienen created_at y más órdenes)
    all_orders = json_orders
    all_errors = csv_errors + json_errors

    # ── 4. DATETIME ─────────────────────────────────────────────────────────
    demo_datetime(all_orders)

    # ── 5. MÉTRICAS ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("6. MÉTRICAS AGREGADAS")
    print("=" * 70)
    metrics = compute_metrics(all_orders)

    print(f"\n   Total órdenes   : {metrics.get('total_orders')}")
    print(f"   Revenue total   : ${metrics.get('total_revenue', 0):.2f}")
    print(f"   Ticket promedio : ${metrics.get('avg_order_value', 0):.2f}")

    print("\n   Top 3 productos:")
    for p in metrics.get("top_3_products", []):
        print(f"      {p['product_name']:35} x{p['total_quantity']}")

    print("\n   Clientes por gasto:")
    for name, data in list(metrics.get("by_customer", {}).items())[:5]:
        print(f"      {name:20}  {data['order_count']} órdenes  ${data['total_spent']:.2f}")

    # ── 6. EXPORTAR JSON ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("7. EXPORTAR RESULTADOS A JSON")
    print("=" * 70)
    export_metrics_to_json(metrics, all_errors, output_path)
    print(f"\n   ✓ Archivo generado: {output_path.resolve()}")

    # ── 7. SUBPROCESS ───────────────────────────────────────────────────────
    demo_subprocess()

    # ── FIN ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("✓ LABORATORIO MÓDULO 6 COMPLETADO")
    print(f"  Log guardado en: {Path('orders_lab.log').resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
