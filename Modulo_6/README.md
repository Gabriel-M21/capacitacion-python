# Módulo 6 - Librería estándar y entrada/salida

## Objetivo

Manipular rutas y archivos, procesar CSV/JSON, manejar fechas y registrar eventos mediante el módulo `logging`.

## Qué se realizó

- Lectura y escritura de CSV y JSON.
- Cálculo de métricas sobre pedidos.
- Uso de `pathlib` para rutas portables.
- Configuración de logging en niveles y archivo de salida.
- Demostración en `scripts/demo_module_6.py`.

## Ejecución

Abre CMD en la raíz del repositorio:

```cmd
cd /d Modulo_6
poetry install
poetry run python scripts/demo_module_6.py
```

Revisa `data/` para los archivos de entrada y las exportaciones generadas por el ejemplo.

```cmd
poetry run ruff check src/ scripts/
```

Este módulo todavía no contiene archivos de pruebas `test_*.py`.
