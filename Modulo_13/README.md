# Módulo 13 - Patrones de diseño

## Objetivo

Aplicar patrones creacionales, estructurales y de comportamiento a la lógica de pedidos.

## Qué se realizó

- Strategy para `none`, `volume`, `seasonal`, `vip` y `max`.
- Builder para construir órdenes normales y exprés.
- Decorator de caché para el cliente de catálogo.
- Adapter de infraestructura para estrategias de precio.
- Demostración en `scripts/demo_module_13.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_13
poetry install
poetry run python scripts/demo_module_13.py
poetry run pytest -q tests/test_patterns.py tests/test_pricing.py
```

La demostración es local y no requiere levantar FastAPI, Docker ni Smocker. Los
patrones Strategy, Builder, Adapter y Decorator se ejecutan directamente desde el
script; este módulo todavía no publica endpoints HTTP para esos ejemplos.
