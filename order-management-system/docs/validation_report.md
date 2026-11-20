# Reporte de Validación — Order Management System

**Fecha:** 2026-11-20 18:58 UTC  
**Duración total:** 41.7 segundos  
**Resultado:** 9/10 pasos exitosos  

---

## Resumen ejecutivo

| # | Paso | Estado | Resultado |
|---|------|--------|-----------|
| 1 | Tipado estático (mypy) | OK | Success: no issues found in 70 source files |
| 2 | Linting (ruff) | OK | All checks passed! |
| 3 | Formato (black) | OK | 70 files would be left unchanged. |
| 4 | Orden de imports (isort) | OK | Sin cambios necesarios |
| 5 | Pruebas (pytest) | OK | ================= 150 passed, 1 skipped, 5 warnings in 7.77s ================== |
| 6 | Auditoría de dependencias (pip-audit) | FAIL | 105 dependencias auditadas (1 omitidas) — 2 hallazgos únicos en 2 paquetes |
| 7 | Docker build (multistage) | OK | Build exitoso — imagen: 1003 MB |
| 8 | Migraciones (Alembic) | OK | 3 migraciones en historial |
| 9 | Empaquetado (wheel) | OK | order_management_system-0.1.0-py3-none-any.whl (62.8 KB) |
| 10 | API health check | OK | HTTP 200 — {'status': 'ok', 'service': 'order-management-api'} |

---

## Detalle por sección

### Calidad de código

- OK **Tipado estático (mypy)**: Success: no issues found in 70 source files
- OK **Linting (ruff)**: All checks passed!
- OK **Formato (black)**: 70 files would be left unchanged.
- OK **Orden de imports (isort)**: Sin cambios necesarios

### Pruebas

- OK **Pruebas (pytest)**
  - Tests pasados: **150**
  - Tests fallidos: **0**
  - Skipped: **1**
  - Cobertura total: **54%**
  - Resumen: `================= 150 passed, 1 skipped, 5 warnings in 7.77s ==================`

### Seguridad — Auditoría de dependencias

- FAIL **Auditoría de dependencias (pip-audit)**
  - 105 dependencias auditadas (1 omitidas) — 2 hallazgos únicos en 2 paquetes

  | Paquete | Versión | CVE | Fix disponible |
  |---------|---------|-----|----------------|
  | ecdsa | 0.19.2 | PYSEC-2026-1325 | No disponible |
  | python-jose | 3.5.0 | PYSEC-2026-4298 | No disponible |

### Docker

- OK **Docker build (multistage)**: Build exitoso — imagen: 1003 MB

### Migraciones Alembic

- `7e5d62d6fe39 -> 90582d06df97 (head), add hashed_password and role to users`
- `bda6c295ed89 -> 7e5d62d6fe39, add hashed_password and role to users`
- `<base> -> bda6c295ed89, create users orders order_items tables`

### Empaquetado

- OK **Empaquetado (wheel)**: order_management_system-0.1.0-py3-none-any.whl (62.8 KB)

### API

- OK **API health check**: HTTP 200 — {'status': 'ok', 'service': 'order-management-api'}

---

## Conclusión

**1 paso(s) requieren atención** antes de la entrega final.

---

_Reporte generado automáticamente por `scripts/run_full_validation.py`_