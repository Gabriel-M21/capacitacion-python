"""
Script de verificación de endpoints - Proyecto Final
Envía peticiones a todos los endpoints de la API y reporta resultados.

Requisito: API corriendo en http://localhost:8000
  poetry run uvicorn order_management.api.main:app --reload

Uso:
  poetry run python scripts/verify_endpoints.py
"""

import json
import os
import sys
import time
from typing import Any

import httpx

BASE_URL = os.environ.get("ORDERS_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 15.0

# Colores para consola
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {YELLOW}→{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")


results: list[dict[str, Any]] = []


def check(
    label: str,
    response: httpx.Response,
    expected_status: int,
    show_body: bool = False,
) -> dict[str, Any] | None:
    """Verifica el status code y registra el resultado."""
    passed = response.status_code == expected_status
    duration = response.elapsed.total_seconds() if response.elapsed else 0

    if passed:
        ok(f"{label} [{response.status_code}] ({duration:.3f}s)")
    else:
        fail(
            f"{label} — esperado {expected_status}, "
            f"recibido {response.status_code} ({duration:.3f}s)"
        )

    body: Any = None
    try:
        body = response.json()
        if show_body and body:
            snippet = json.dumps(body, ensure_ascii=False)[:200]
            info(f"Body: {snippet}{'...' if len(str(body)) > 200 else ''}")
    except Exception:
        body = response.text[:100]

    result = {
        "label": label,
        "method": "",
        "url": str(response.url),
        "status": response.status_code,
        "expected": expected_status,
        "passed": passed,
        "duration_s": round(duration, 3),
        "body_preview": str(body)[:100] if body else "",
    }
    results.append(result)
    return body if passed else None


# ---------------------------------------------------------------------------
# PASO 0 — Health check y login
# ---------------------------------------------------------------------------


def step_health(client: httpx.Client) -> bool:
    section("0. HEALTH CHECK")
    resp = client.get(f"{BASE_URL}/health")
    body = check("GET /health", resp, 200, show_body=True)
    return body is not None


def step_login(client: httpx.Client) -> str | None:
    section("1. AUTENTICACIÓN — POST /auth/login")
    resp = client.post(
        f"{BASE_URL}/auth/login",
        data={"username": "admin@example.com", "password": "admin123"},
    )
    body = check("POST /auth/login (admin)", resp, 200, show_body=True)
    if body:
        token = body.get("access_token")
        ok("Token de acceso obtenido")
        return token

    # Si falla, intentar con user
    resp2 = client.post(
        f"{BASE_URL}/auth/login",
        data={"username": "user@example.com", "password": "user123"},
    )
    body2 = check("POST /auth/login (user)", resp2, 200)
    return body2.get("access_token") if body2 else None


# ---------------------------------------------------------------------------
# PASO 1 — CRUD básico (Módulo 9)
# ---------------------------------------------------------------------------


def step_crud(client: httpx.Client, headers: dict[str, str]) -> str | None:
    section("2. CRUD BÁSICO — Módulo 9")

    # Sin auth → 401
    resp = client.get(f"{BASE_URL}/orders")
    check("GET /orders (sin token) → 401", resp, 401)

    # Listar (vacío o con datos)
    resp = client.get(f"{BASE_URL}/orders", headers=headers)
    check("GET /orders", resp, 200, show_body=False)

    # Crear orden
    payload = {
        "customer": {
            "name": "Test Script",
            "email": "script@example.com",
            "phone": "+52 55 0000 0000",
        },
        "items": [
            {"product_name": "Laptop Test", "quantity": 1, "unit_price": 999.99},
            {"product_name": "Mouse Test", "quantity": 2, "unit_price": 29.99},
        ],
        "notes": "Creada por verify_endpoints.py",
    }
    resp = client.post(f"{BASE_URL}/orders", json=payload, headers=headers)
    body = check("POST /orders", resp, 201, show_body=True)
    order_id: str | None = body.get("order_id") if body else None

    if order_id:
        ok(f"order_id obtenido: {order_id}")

        # Obtener por ID
        resp = client.get(f"{BASE_URL}/orders/{order_id}", headers=headers)
        check(f"GET /orders/{order_id}", resp, 200)

        # 404
        resp = client.get(f"{BASE_URL}/orders/ORD-99999", headers=headers)
        check("GET /orders/ORD-99999 → 404", resp, 404)

        # Payload inválido → 422
        resp = client.post(
            f"{BASE_URL}/orders",
            json={"customer": {"name": "", "email": "mal"}, "items": []},
            headers=headers,
        )
        check("POST /orders (payload inválido) → 422", resp, 422)

        # Cambiar estado: pending → confirmed
        resp = client.patch(
            f"{BASE_URL}/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=headers,
        )
        check(f"PATCH /orders/{order_id}/status → confirmed", resp, 200)

        # Transición inválida: confirmed → delivered
        resp = client.patch(
            f"{BASE_URL}/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=headers,
        )
        check(f"PATCH /orders/{order_id}/status (inválida) → 422", resp, 422)

        # Estado inválido
        resp = client.patch(
            f"{BASE_URL}/orders/{order_id}/status",
            json={"status": "inventado"},
            headers=headers,
        )
        check("PATCH status inválido → 422", resp, 422)

        # Crear segunda orden para delete
        resp2 = client.post(f"{BASE_URL}/orders", json=payload, headers=headers)
        body2 = check("POST /orders (segunda, para delete)", resp2, 201)
        order_id2 = body2.get("order_id") if body2 else None

        if order_id2:
            resp = client.delete(f"{BASE_URL}/orders/{order_id2}", headers=headers)
            check(f"DELETE /orders/{order_id2}", resp, 204)

            resp = client.get(f"{BASE_URL}/orders/{order_id2}", headers=headers)
            check(f"GET /orders/{order_id2} (eliminada) → 404", resp, 404)

    return order_id


# ---------------------------------------------------------------------------
# PASO 2 — Herramientas (Módulos 10-16)
# ---------------------------------------------------------------------------


def step_tools(client: httpx.Client, headers: dict[str, str]) -> None:

    # ── Módulo 10: volume discount ────────────────────────────────────────
    section("3. MÓDULO 10 — TDD: volume_discount")
    for n, expected_pct in [(1, 0), (3, 5), (6, 10), (10, 15)]:
        resp = client.get(f"{BASE_URL}/orders/tools/volume-discount/{n}", headers=headers)
        body = check(f"GET /tools/volume-discount/{n}", resp, 200)
        if body:
            actual_pct = body.get("discount_percentage")
            if not isinstance(actual_pct, int | float) or actual_pct != expected_pct:
                fail(f"  {n} items → esperado {expected_pct}%, " f"recibido {actual_pct}%")
                results[-1]["passed"] = False
            else:
                info(f"  {n} items → {actual_pct}% descuento")

    resp = client.get(f"{BASE_URL}/orders/tools/volume-discount/0", headers=headers)
    check("GET /tools/volume-discount/0 → 422", resp, 422)

    # ── Módulo 11: concurrency benchmark ─────────────────────────────────
    section("4. MÓDULO 11 — Concurrencia: async vs sync")
    resp = client.get(
        f"{BASE_URL}/orders/tools/concurrency-benchmark?n_orders=5",
        headers=headers,
        timeout=30.0,
    )
    body = check("GET /tools/concurrency-benchmark", resp, 200, show_body=True)
    if body:
        info(
            f"  sync: {body.get('sync_time_s')}s  async: {body.get('async_time_s')}s  speedup: {body.get('speedup')}x"
        )

    # ── Módulo 12: validate ────────────────────────────────────────────────
    section("5. MÓDULO 12 — SOLID: validate")
    # Válida
    resp = client.post(
        f"{BASE_URL}/orders/tools/validate",
        json={
            "order_id": "ORD-001",
            "customer_name": "Juan",
            "email": "juan@example.com",
            "status": "pending",
            "items": [{"product_name": "P", "quantity": 1, "price": 10.0}],
        },
        headers=headers,
    )
    body = check("POST /tools/validate (válida)", resp, 200)
    if body:
        info(f"  valid={body.get('valid')}  message={body.get('message')}")

    # Inválida
    resp = client.post(
        f"{BASE_URL}/orders/tools/validate",
        json={"order_id": "X", "customer_name": "", "status": "pending", "items": []},
        headers=headers,
    )
    body = check("POST /tools/validate (inválida)", resp, 200)
    if body:
        info(f"  valid={body.get('valid')}  message={body.get('message')}")

    # ── Módulo 13: pricing strategy ────────────────────────────────────────
    section("6. MÓDULO 13 — Strategy de precios")
    for strategy in ["none", "volume", "seasonal", "vip", "max"]:
        resp = client.post(
            f"{BASE_URL}/orders/tools/pricing-strategy",
            json={
                "strategy": strategy,
                "item_count": 6,
                "total": 1000.0,
                "email": "laura.gomez@example.com",
                "vip_emails": ["laura.gomez@example.com"],
                "seasonal_pct": 12.0,
            },
            headers=headers,
        )
        body = check(f"POST /tools/pricing-strategy ({strategy})", resp, 200)
        if body:
            info(
                f"  descuento={body.get('discount_percentage')}%  total_final=${body.get('total_final'):.2f}"
            )

    # Estrategia inválida
    resp = client.post(
        f"{BASE_URL}/orders/tools/pricing-strategy",
        json={"strategy": "inventada", "item_count": 1, "total": 100.0},
        headers=headers,
    )
    check("POST /tools/pricing-strategy (inválida) → 422", resp, 422)

    # ── Módulo 13: builder ────────────────────────────────────────────────
    section("7. MÓDULO 13 — Builder Pattern")
    resp = client.post(
        f"{BASE_URL}/orders/tools/builder",
        json={
            "customer_name": "Ana Builder",
            "customer_email": "ana.builder@example.com",
            "express": False,
            "notes": "Orden via Builder",
            "items": [
                {"product_name": "Laptop Builder", "quantity": 1, "unit_price": 1299.99},
            ],
        },
        headers=headers,
    )
    body = check("POST /tools/builder (normal)", resp, 201, show_body=True)
    if body:
        info(f"  order_id={body.get('order_id')}  status={body.get('status')}")

    # Express
    resp = client.post(
        f"{BASE_URL}/orders/tools/builder",
        json={
            "customer_name": "VIP Express",
            "customer_email": "vip@example.com",
            "express": True,
            "items": [{"product_name": "MacBook", "quantity": 1, "unit_price": 2499.99}],
        },
        headers=headers,
    )
    body = check("POST /tools/builder (express)", resp, 201)
    if body:
        info(
            f"  order_id={body.get('order_id')}  express={body.get('express')}  status={body.get('status')}"
        )

    # ── Módulo 14: ML inference ───────────────────────────────────────────
    section("8. MÓDULO 14 — ML: inferencia joblib")
    resp = client.post(
        f"{BASE_URL}/orders/tools/ml-inference",
        json={
            "order_total": 1500.0,
            "item_count": 2,
            "hour": 10,
            "day_of_week": 1,
            "month": 3,
        },
        headers=headers,
    )
    if resp.status_code == 404:
        info("Modelo no encontrado (ejecuta demo_module_14.py primero) — SKIPPED")
        results.append(
            {
                "label": "POST /tools/ml-inference",
                "passed": None,
                "status": resp.status_code,
                "expected": 200,
                "duration_s": 0,
                "body_preview": "Skipped — modelo no entrenado",
            }
        )
    else:
        body = check("POST /tools/ml-inference", resp, 200, show_body=True)
        if body:
            info(f"  prediccion={body.get('prediction')}  confianza={body.get('confidence'):.1%}")

    # ── Módulo 14: CSV metrics ────────────────────────────────────────────
    section("9. MÓDULO 14 — Pandas: métricas CSV")
    resp = client.get(f"{BASE_URL}/orders/tools/csv-metrics", headers=headers)
    if resp.status_code == 404:
        info("CSV no encontrado (data/orders_extended.csv) — SKIPPED")
        results.append(
            {
                "label": "GET /tools/csv-metrics",
                "passed": None,
                "status": resp.status_code,
                "expected": 200,
                "duration_s": 0,
                "body_preview": "Skipped — CSV no encontrado",
            }
        )
    else:
        body = check("GET /tools/csv-metrics", resp, 200, show_body=True)
        if body:
            info(f"  ordenes={body.get('unique_orders')}  revenue=${body.get('total_revenue')}")

    # ── Módulos 15/16: use-case ───────────────────────────────────────────
    section("10. MÓDULOS 15/16 — Hexagonal: CreateOrderUseCase")
    for presenter in ["json", "cli", "audit"]:
        resp = client.post(
            f"{BASE_URL}/orders/tools/use-case",
            json={
                "customer_name": f"UseCase {presenter.upper()}",
                "customer_email": f"usecase.{presenter}@example.com",
                "presenter": presenter,
                "notes": f"Creada con presenter={presenter}",
                "items": [
                    {"product_name": "Producto UseCase", "quantity": 1, "unit_price": 199.99}
                ],
            },
            headers=headers,
        )
        body = check(f"POST /tools/use-case (presenter={presenter})", resp, 201)
        if body:
            events = body.get("events_published", [])
            info(f"  eventos publicados: {len(events)}")
            if events:
                info(f"    {events[0]}")

    # Presenter inválido
    resp = client.post(
        f"{BASE_URL}/orders/tools/use-case",
        json={
            "customer_name": "X",
            "customer_email": "x@x.com",
            "presenter": "invalido",
            "items": [{"product_name": "P", "quantity": 1, "unit_price": 1.0}],
        },
        headers=headers,
    )
    check("POST /tools/use-case (presenter inválido) → 422", resp, 422)

    # ── Capabilities map ──────────────────────────────────────────────────
    section("11. MAPA DE CAPACIDADES")
    resp = client.get(f"{BASE_URL}/orders/tools/capabilities", headers=headers)
    body = check("GET /tools/capabilities", resp, 200)
    if body:
        total = body.get("total_modulos_expuestos", 0)
        info(f"  Módulos expuestos: {total}")


# ---------------------------------------------------------------------------
# RESUMEN FINAL
# ---------------------------------------------------------------------------


def print_summary() -> int:
    section("RESUMEN DE VERIFICACIÓN")

    passed = [r for r in results if r.get("passed") is True]
    failed = [r for r in results if r.get("passed") is False]
    skipped = [r for r in results if r.get("passed") is None]

    total = len(results)
    print(f"\n  Total comprobaciones HTTP   : {total}")
    print(f"  {GREEN}Pasaron{RESET}                    : {len(passed)}")
    print(f"  {RED}Fallaron{RESET}                   : {len(failed)}")
    print(f"  {YELLOW}Saltados (no disponibles){RESET}  : {len(skipped)}")

    if failed:
        print(f"\n  {RED}Endpoints fallidos:{RESET}")
        for r in failed:
            print(f"    {RED}✗{RESET} {r['label']} " f"[{r['status']} ≠ {r['expected']}]")

    if skipped:
        print(f"\n  {YELLOW}Saltados:{RESET}")
        for r in skipped:
            print(f"    {YELLOW}→{RESET} {r['label']} — {r.get('body_preview', '')}")

    pct = round(len(passed) / max(len(passed) + len(failed), 1) * 100)
    print(f"\n  Resultado: {pct}% de comprobaciones HTTP correctas")

    if len(failed) == 0:
        print(f"\n  {GREEN}{BOLD}✓ Todos los endpoints disponibles funcionan correctamente{RESET}")
    else:
        print(f"\n  {RED}{BOLD}✗ Hay {len(failed)} endpoint(s) con errores{RESET}")

    return len(failed)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  VERIFICACIÓN DE ENDPOINTS — Order Management System{RESET}")
    print(f"{BOLD}  API: {BASE_URL}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    t0 = time.perf_counter()

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:

        # Verificar que la API está corriendo
        try:
            client.get("/health")
        except httpx.ConnectError:
            print(f"\n{RED}ERROR: No se puede conectar a {BASE_URL}{RESET}")
            print("Levanta la API con:")
            print("  poetry run uvicorn order_management.api.main:app --reload\n")
            sys.exit(1)

        # Health
        if not step_health(client):
            print(f"{RED}Health check falló. Abortando.{RESET}")
            sys.exit(1)

        # Login
        token = step_login(client)
        if not token:
            print(f"{RED}Login falló. Verifica que los usuarios están creados.{RESET}")
            sys.exit(1)

        headers = {"Authorization": f"Bearer {token}"}

        # CRUD básico
        step_crud(client, headers)

        # Herramientas de módulos
        step_tools(client, headers)

    elapsed = time.perf_counter() - t0
    print(f"\n  Tiempo total: {elapsed:.2f}s")

    n_failed = print_summary()
    print(f"\n{'=' * 60}\n")
    sys.exit(0 if n_failed == 0 else 1)


if __name__ == "__main__":
    main()
