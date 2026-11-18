"""
Demo del Módulo 14: Ciencia de datos
- Ingesta con Pandas y Polars (comparación)
- Limpieza y feature engineering
- Clasificador de estado de orden con scikit-learn
- Serialización con joblib
- Inferencia básica
- Llenado de la base de datos SQLite (Módulo 8)
"""

import logging
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import polars as pl
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from order_management.infrastructure.db.base import Base
from order_management.infrastructure.db import models  # noqa: F401
from order_management.infrastructure.db.session import build_engine
from order_management.infrastructure.db.repositories.order_repository import (
    OrderRepository,
)
from order_management.services.order_builder import OrderBuilder
from order_management.domain.value_objects import OrderId, OrderStatus

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CSV_PATH   = Path("data") / "orders_extended.csv"
MODEL_PATH = Path("data") / "output" / "order_classifier.joblib"
DB_URL     = "sqlite:///order_management.db"


# ---------------------------------------------------------------------------
# PARTE 1A — Ingesta con PANDAS
# ---------------------------------------------------------------------------

def ingest_with_pandas(path: Path) -> pd.DataFrame:
    """Carga y limpia el CSV usando Pandas."""
    print("\n" + "=" * 65)
    print("1A. INGESTA CON PANDAS")
    print("=" * 65)

    df = pd.read_csv(path, encoding="utf-8")
    print(f"\n  Filas cargadas    : {len(df)}")
    print(f"  Columnas          : {list(df.columns)}")
    print(f"\n  Tipos de datos:")
    for col, dtype in df.dtypes.items():
        print(f"    {col:<20} {dtype}")

    # Limpieza
    before = len(df)
    df = df.dropna(subset=["order_id", "customer_name", "email", "product_name"])
    df = df[df["price"] > 0]
    df = df[df["quantity"] > 0]
    df = df[df["status"].isin(["pending", "confirmed", "shipped", "delivered", "cancelled"])]
    after = len(df)

    print(f"\n  Filas antes limpieza : {before}")
    print(f"  Filas después        : {after}")
    print(f"  Eliminadas           : {before - after}")

    # Parseo de fechas
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Feature engineering
    df["subtotal"]    = df["price"] * df["quantity"]
    df["hour"]        = df["created_at"].dt.hour
    df["day_of_week"] = df["created_at"].dt.dayofweek
    df["month"]       = df["created_at"].dt.month

    # Totales por orden
    order_totals = df.groupby("order_id")["subtotal"].sum().rename("order_total")
    order_items  = df.groupby("order_id")["product_name"].count().rename("item_count")
    df = df.merge(order_totals, on="order_id").merge(order_items, on="order_id")

    print(f"\n  Distribución de estados:")
    for status, count in df.drop_duplicates("order_id")["status"].value_counts().items():
        print(f"    {status:<12} : {count}")

    print(f"\n  Estadísticas de order_total:")
    stats = df.drop_duplicates("order_id")["order_total"].describe()
    print(f"    media  : ${stats['mean']:.2f}")
    print(f"    mediana: ${stats['50%']:.2f}")
    print(f"    máximo : ${stats['max']:.2f}")

    return df


# ---------------------------------------------------------------------------
# PARTE 1B — Ingesta con POLARS
# ---------------------------------------------------------------------------

def ingest_with_polars(path: Path) -> pl.DataFrame:
    """Carga y limpia el CSV usando Polars."""
    print("\n" + "=" * 65)
    print("1B. INGESTA CON POLARS")
    print("=" * 65)

    df = pl.read_csv(path, encoding="utf8")
    print(f"\n  Filas cargadas    : {len(df)}")
    print(f"  Columnas          : {df.columns}")

    print(f"\n  Schema:")
    for col, dtype in df.schema.items():
        print(f"    {col:<20} {dtype}")

    # Limpieza — Polars usa expresiones lazy
    before = len(df)
    df = (
        df
        .filter(pl.col("order_id").is_not_null())
        .filter(pl.col("customer_name").is_not_null() & (pl.col("customer_name") != ""))
        .filter(pl.col("email").is_not_null() & (pl.col("email") != ""))
        .filter(pl.col("product_name").is_not_null() & (pl.col("product_name") != ""))
        .filter(pl.col("price").cast(pl.Float64, strict=False).is_not_null())
        .filter(pl.col("price").cast(pl.Float64) > 0)
        .filter(pl.col("quantity").cast(pl.Float64) > 0)
        .filter(pl.col("status").is_in(["pending", "confirmed", "shipped", "delivered", "cancelled"]))
    )
    after = len(df)

    print(f"\n  Filas antes limpieza : {before}")
    print(f"  Filas después        : {after}")
    print(f"  Eliminadas           : {before - after}")

    # Feature engineering con Polars
    df = df.with_columns([
        (pl.col("price") * pl.col("quantity")).alias("subtotal"),
        pl.col("created_at").str.to_datetime("%Y-%m-%d %H:%M:%S").alias("created_dt"),
    ])

    df = df.with_columns([
        pl.col("created_dt").dt.hour().alias("hour"),
        pl.col("created_dt").dt.weekday().alias("day_of_week"),
        pl.col("created_dt").dt.month().alias("month"),
    ])

    # Totales por orden
    order_agg = df.group_by("order_id").agg([
        pl.col("subtotal").sum().alias("order_total"),
        pl.col("product_name").count().alias("item_count"),
    ])
    df = df.join(order_agg, on="order_id")

    print(f"\n  Distribución de estados (Polars):")
    status_counts = (
        df.unique("order_id")
        .group_by("status")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    for row in status_counts.iter_rows(named=True):
        print(f"    {row['status']:<12} : {row['count']}")

    print(f"\n  Top 5 productos por revenue:")
    top = (
        df.group_by("product_name")
        .agg(pl.col("subtotal").sum().alias("revenue"))
        .sort("revenue", descending=True)
        .head(5)
    )
    for row in top.iter_rows(named=True):
        print(f"    {row['product_name']:<35} ${row['revenue']:.2f}")

    return df


# ---------------------------------------------------------------------------
# PARTE 2 — Clasificador con scikit-learn
# ---------------------------------------------------------------------------

def train_classifier(df: pd.DataFrame) -> tuple:
    """Entrena un RandomForest para predecir el estado de una orden."""
    print("\n" + "=" * 65)
    print("2. CLASIFICADOR — RandomForestClassifier")
    print("=" * 65)

    # Features a nivel de orden (una fila por orden)
    order_df = (
        df.drop_duplicates("order_id")[
            ["order_id", "status", "order_total", "item_count", "hour", "day_of_week", "month"]
        ]
        .copy()
    )

    print(f"\n  Órdenes únicas para entrenamiento: {len(order_df)}")

    # Encode target
    le = LabelEncoder()
    order_df["status_encoded"] = le.fit_transform(order_df["status"])

    print(f"  Clases: {list(le.classes_)}")

    # Features y target
    feature_cols = ["order_total", "item_count", "hour", "day_of_week", "month"]
    X = order_df[feature_cols].values
    y = order_df["status_encoded"].values

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train : {len(X_train)} órdenes")
    print(f"  Test  : {len(X_test)} órdenes")

    # Entrenar
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    # Evaluar
    y_pred = clf.predict(X_test)
    accuracy = (y_pred == y_test).mean()
    print(f"\n  Accuracy: {accuracy:.3f} ({accuracy:.1%})")

    print(f"\n  Reporte de clasificación:")
    report = classification_report(
        y_test, y_pred,
        target_names=le.classes_,
        zero_division=0,
    )
    for line in report.split("\n"):
        if line.strip():
            print(f"    {line}")

    print(f"\n  Importancia de features:")
    for feat, imp in sorted(
        zip(feature_cols, clf.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    ):
        bar = "█" * int(imp * 40)
        print(f"    {feat:<15} {imp:.3f}  {bar}")

    return clf, le, feature_cols


# ---------------------------------------------------------------------------
# PARTE 3 — Serialización con joblib
# ---------------------------------------------------------------------------

def save_model(clf: RandomForestClassifier, le: LabelEncoder, feature_cols: list) -> None:
    """Guarda el modelo y el encoder con joblib."""
    print("\n" + "=" * 65)
    print("3. SERIALIZACIÓN — joblib")
    print("=" * 65)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {"clf": clf, "le": le, "feature_cols": feature_cols}
    joblib.dump(bundle, MODEL_PATH)
    size_kb = MODEL_PATH.stat().st_size / 1024
    print(f"\n  Modelo guardado en : {MODEL_PATH.resolve()}")
    print(f"  Tamaño             : {size_kb:.1f} KB")


def load_and_infer(examples: list[dict]) -> None:
    """Carga el modelo y hace inferencia sobre ejemplos nuevos."""
    print("\n" + "=" * 65)
    print("4. INFERENCIA — Cargar modelo y predecir")
    print("=" * 65)

    bundle = joblib.load(MODEL_PATH)
    clf: RandomForestClassifier = bundle["clf"]
    le:  LabelEncoder           = bundle["le"]
    feature_cols: list          = bundle["feature_cols"]

    print(f"\n  Modelo cargado: {type(clf).__name__}")
    print(f"  Features      : {feature_cols}")

    print(f"\n  {'Total':>8}  {'Items':>5}  {'Hora':>4}  {'Día':>3}  {'Mes':>3}  {'Predicción':<12}  {'Confianza':>9}")
    print("  " + "-" * 60)

    for ex in examples:
        X = np.array([[
            ex["order_total"],
            ex["item_count"],
            ex["hour"],
            ex["day_of_week"],
            ex["month"],
        ]])
        pred_encoded  = clf.predict(X)[0]
        probabilities = clf.predict_proba(X)[0]
        pred_label    = le.inverse_transform([pred_encoded])[0]
        confidence    = probabilities.max()

        print(
            f"  ${ex['order_total']:>7.2f}"
            f"  {ex['item_count']:>5}"
            f"  {ex['hour']:>4}"
            f"  {ex['day_of_week']:>3}"
            f"  {ex['month']:>3}"
            f"  {pred_label:<12}"
            f"  {confidence:>8.1%}"
        )


# ---------------------------------------------------------------------------
# PARTE 5 — Llenar la base de datos SQLite (Módulo 8)
# ---------------------------------------------------------------------------

def fill_database(df: pd.DataFrame, max_orders: int = 50) -> None:
    """
    Inserta órdenes del CSV en la base de datos SQLite del Módulo 8,
    usando OrderRepository y OrderBuilder de las clases existentes.
    """
    print("\n" + "=" * 65)
    print("5. LLENAR BASE DE DATOS SQLITE (Módulo 8)")
    print("=" * 65)

    engine = build_engine(DB_URL)
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)

    # Tomar las primeras max_orders órdenes únicas y válidas
    valid_orders = (
        df[df["status"].isin(["pending", "confirmed", "shipped", "delivered", "cancelled"])]
        .drop_duplicates("order_id")
        .head(max_orders)
    )

    inserted = 0
    skipped  = 0

    status_map = {
        "pending":   OrderStatus.PENDING,
        "confirmed": OrderStatus.CONFIRMED,
        "shipped":   OrderStatus.SHIPPED,
        "delivered": OrderStatus.DELIVERED,
        "cancelled": OrderStatus.CANCELLED,
    }

    # Transiciones válidas para avanzar el estado
    transitions = [
        OrderStatus.CONFIRMED,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    ]

    for idx, (_, row) in enumerate(valid_orders.iterrows(), start=1):
        order_id_str = str(row["order_id"])

        # Extraer items de esta orden del dataframe completo
        items_df = df[df["order_id"] == order_id_str]
        if items_df.empty:
            skipped += 1
            continue

        try:
            # Extraer número del order_id (ORD-001 → 1)
            numeric = order_id_str.replace("ORD-", "").lstrip("0") or "0"
            order_num = int(numeric) if numeric.isdigit() else idx + 1000

            builder = (
                OrderBuilder(order_id=OrderId.generate(order_num))
                .with_customer(
                    name=str(row["customer_name"]),
                    email=str(row["email"]),
                )
            )

            for _, item in items_df.iterrows():
                builder = builder.add_item(
                    product_name=str(item["product_name"]),
                    quantity=int(item["quantity"]),
                    unit_price=float(item["price"]),
                )

            order = builder.build()

            # Avanzar al estado real del CSV
            target = status_map.get(str(row["status"]), OrderStatus.PENDING)
            for step in transitions:
                if order.status == target:
                    break
                if order.status.can_transition_to(step):
                    order.change_status(step)
                    if order.status == target:
                        break

            with Session() as session:
                repo = OrderRepository(session)
                repo.save(order)
                session.commit()

            inserted += 1

        except Exception as exc:
            logger.warning("Orden %s omitida: %s", order_id_str, exc)
            skipped += 1

    print(f"\n  Órdenes insertadas : {inserted}")
    print(f"  Omitidas           : {skipped}")
    print(f"  Base de datos      : {DB_URL}")

    # Verificar
    with Session() as session:
        repo    = OrderRepository(session)
        all_ord = repo.list_all()
        print(f"  Total en DB        : {len(all_ord)} órdenes")
        print(f"\n  Muestra (primeras 5):")
        for o in all_ord[:5]:
            print(f"    {o.order_id}  {o.customer.name:<20}  {o.total}  {o.status.value}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 65)
    print("MÓDULO 14: CIENCIA DE DATOS")
    print("Pandas · Polars · scikit-learn · joblib · SQLite")
    print("=" * 65)

    # 1A. Ingesta con Pandas
    df_pandas = ingest_with_pandas(CSV_PATH)

    # 1B. Ingesta con Polars
    df_polars = ingest_with_polars(CSV_PATH)

    # Comparación rápida
    print("\n" + "=" * 65)
    print("COMPARACIÓN PANDAS vs POLARS")
    print("=" * 65)
    print(f"\n  {'Librería':<10} {'Filas limpias':>14}  {'Columnas':>9}")
    print("  " + "-" * 36)
    print(f"  {'Pandas':<10} {len(df_pandas):>14}  {len(df_pandas.columns):>9}")
    print(f"  {'Polars':<10} {len(df_polars):>14}  {len(df_polars.columns):>9}")
    print("""
  Diferencias clave:
  • Pandas: API mutable, integración con sklearn directa
  • Polars: expresiones lazy, más rápido en datasets grandes
  • Ambos leen el mismo CSV y producen resultados equivalentes
    """)

    # 2. Entrenar clasificador
    clf, le, feature_cols = train_classifier(df_pandas)

    # 3. Guardar modelo
    save_model(clf, le, feature_cols)

    # 4. Inferencia con ejemplos nuevos
    examples = [
        {"order_total": 1500.0, "item_count": 2, "hour": 10, "day_of_week": 1, "month": 3},
        {"order_total":   50.0, "item_count": 1, "hour": 20, "day_of_week": 5, "month": 12},
        {"order_total":  350.0, "item_count": 3, "hour": 14, "day_of_week": 2, "month": 6},
        {"order_total": 2500.0, "item_count": 4, "hour":  9, "day_of_week": 0, "month": 1},
        {"order_total":  100.0, "item_count": 1, "hour": 18, "day_of_week": 4, "month": 11},
    ]
    load_and_infer(examples)

    # 5. Llenar base de datos
    fill_database(df_pandas, max_orders=50)

    print("\n" + "=" * 65)
    print("✓ DEMO MÓDULO 14 COMPLETADO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
