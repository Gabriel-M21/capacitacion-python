# Reporte de Auditoría de Dependencias
# Generado con: poetry run pip-audit
# Proyecto: order-management-system v0.1.0

## Resumen

| Métrica | Valor |
|---|---|
| Total dependencias auditadas | 104 |
| Sin vulnerabilidades | 102 |
| Con vulnerabilidades (sin fix) | 2 |
| Fixes disponibles | 0 |

---

## Vulnerabilidades encontradas

### 1. ecdsa 0.19.2
- **CVE**: CVE-2024-23342 (PYSEC-2026-1325, GHSA-wj6h-64fc-37mp)
- **Fix disponible**: No
- **Severidad**: Media
- **Descripción**: python-ecdsa es vulnerable a un ataque de timing Minerva
  en la curva P-256. Usando la función `ecdsa.SigningKey.sign_digest()` y
  midiendo tiempos de firma, un atacante puede filtrar el nonce interno y
  potencialmente descubrir la clave privada.
- **Impacto en este proyecto**: ecdsa es una dependencia transitiva de
  `python-jose`. No se usa directamente.
- **Acción tomada**: Riesgo aceptado — el proyecto usa python-jose solo para
  firmar tokens HS256 (HMAC), no ECDSA. La vulnerabilidad no aplica a este
  caso de uso. Pendiente migración a PyJWT.

### 2. python-jose 3.5.0
- **CVE**: CVE-2026-85394 (PYSEC-2026-4298, GHSA-3qf3-8w2g-rqmx)
- **Fix disponible**: No
- **Severidad**: Alta
- **Descripción**: python-jose 3.5.0 no valida correctamente claves asimétricas
  en la inicialización HMAC, aceptando claves públicas en formato DER sin
  armadura PEM. Atacantes con la clave pública del servicio pueden forjar
  tokens HS256 si los algoritmos no se restringen explícitamente.
- **Impacto en este proyecto**: El proyecto usa HS256 con SECRET_KEY simétrica.
  Los algoritmos se especifican explícitamente en `jwt.py` via
  `algorithms=[settings.algorithm]`, lo que mitiga parcialmente el riesgo.
- **Acción tomada**: Riesgo aceptado con mitigación — algoritmo siempre
  especificado explícitamente. Pendiente migración a PyJWT.

---

## Dependencias limpias destacadas

| Paquete | Versión | Notas |
|---------|---------|-------|
| fastapi | 0.165.0 | Sin vulnerabilidades |
| sqlalchemy | 2.1.8 | Sin vulnerabilidades |
| pydantic | 2.14.3 | Sin vulnerabilidades |
| uvicorn | 0.32.1 | Sin vulnerabilidades |
| httpx | 0.27.2 | Sin vulnerabilidades |
| alembic | 1.20.1 | Sin vulnerabilidades |
| starlette | 1.10.0 | Sin vulnerabilidades |
| cryptography | 50.0.2 | Sin vulnerabilidades |

---

## Plan de remediación

1. **Corto plazo**: Migrar de `python-jose` a `PyJWT` en la próxima iteración.
   `python-jose` está sin mantenimiento activo para estas vulnerabilidades.

2. **Largo plazo**: Configurar renovación automática de auditoría en el pipeline
   CI (ya incluido en `.github/workflows/ci.yml`).

---

## Comando de reproducción

```bash
poetry run pip-audit --format json -o docs/pip-audit-report.json
poetry run pip-audit > docs/pip-audit-report.txt
```
