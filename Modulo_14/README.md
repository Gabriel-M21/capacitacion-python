# Módulo 14 - Ciencia de datos

## Objetivo

Cargar datos de pedidos con Pandas, calcular métricas, entrenar un clasificador y serializarlo para inferencia.

## Qué se realizó

- Carga y análisis de `data/orders_extended.csv`.
- Métricas con Pandas.
- Entrenamiento de modelo con scikit-learn.
- Exportación e inferencia con `joblib`.
- Demostración ejecutable en `scripts/demo_module_14.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_14
poetry install
poetry run python scripts/demo_module_14.py
```

La demo lee `data/orders_extended.csv`, entrena e infiere localmente, guarda el
modelo en `data/output/order_classifier.joblib` y llena la base SQLite local
`order_management.db`. No requiere API web ni Docker. El script crea las tablas
SQLite; ejecútalo desde `Modulo_14` para que encuentre las rutas de datos.

Pruebas del código disponible:

```cmd
poetry run pytest -q
```
