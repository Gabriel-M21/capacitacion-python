"""
Script de validación completa del proyecto final
Ejecuta: tests, mypy, ruff, black, isort, pip-audit, docker build
y genera un reporte Markdown con todos los resultados.

Uso:
    poetry run python scripts/run_full_validation.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPORT_PATH = Path("docs") / "validation_report.md"
API_BASE_URL = os.environ.get("ORDERS_API_URL", "http://localhost:8000").rstrip("/")
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run(
    cmd: list[str],
    capture: bool = True,
    timeout: int = 300,
) -> tuple[int, str, str]:
    """Ejecuta un comando y retorna (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout or "", result.stderr or ""


def status_icon(ok: bool) -> str:
    return f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"


def md_icon(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def print_step(step: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"  {step}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Pasos de validación
# ---------------------------------------------------------------------------


def step_mypy() -> dict:
    print_step("1. TIPADO ESTÁTICO — mypy")
    code, stdout, stderr = run(["poetry", "run", "mypy", "src/", "scripts/", "tests/"])
    ok = code == 0
    output = stdout + stderr
    # Extraer resumen
    lines = output.strip().splitlines()
    summary = next((line for line in reversed(lines) if line.strip()), "Sin salida")
    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Tipado estático (mypy)",
        "ok": ok,
        "summary": summary,
        "detail": output,
    }


def step_ruff() -> dict:
    print_step("2. LINTING — ruff")
    code, stdout, stderr = run(["poetry", "run", "ruff", "check", "src/", "scripts/", "tests/"])
    ok = code == 0
    output = stdout + stderr
    summary = "All checks passed!" if ok else output.strip().splitlines()[0]
    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Linting (ruff)",
        "ok": ok,
        "summary": summary,
        "detail": output,
    }


def step_black() -> dict:
    print_step("3. FORMATO — black")
    code, stdout, stderr = run(["poetry", "run", "black", "--check", "src/", "scripts/", "tests/"])
    ok = code == 0
    output = stdout + stderr
    lines = output.strip().splitlines()
    summary = next((line for line in reversed(lines) if line.strip()), "Sin salida")
    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Formato (black)",
        "ok": ok,
        "summary": summary,
        "detail": output,
    }


def step_isort() -> dict:
    print_step("4. ORDEN DE IMPORTS — isort")
    code, stdout, stderr = run(
        ["poetry", "run", "isort", "--check-only", "src/", "scripts/", "tests/"]
    )
    ok = code == 0
    output = stdout + stderr
    summary = "Sin cambios necesarios" if ok else output.strip()
    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Orden de imports (isort)",
        "ok": ok,
        "summary": summary,
        "detail": output,
    }


def step_pytest() -> dict:
    print_step("5. PRUEBAS — pytest + cobertura")
    code, stdout, stderr = run(
        [
            "poetry",
            "run",
            "pytest",
            "--tb=short",
            "-q",
        ],
        timeout=120,
    )
    ok = code == 0
    output = stdout + stderr
    lines = output.strip().splitlines()

    # Extraer métricas
    passed = failed = skipped = 0
    coverage_total = "N/A"
    summary_line = ""

    for line in lines:
        if "passed" in line or "failed" in line or "error" in line:
            summary_line = line.strip()
        if "passed" in line:
            import re

            m = re.search(r"(\d+) passed", line)
            if m:
                passed = int(m.group(1))
        if "failed" in line:
            import re

            m = re.search(r"(\d+) failed", line)
            if m:
                failed = int(m.group(1))
        if "skipped" in line:
            import re

            m = re.search(r"(\d+) skipped", line)
            if m:
                skipped = int(m.group(1))
        if "TOTAL" in line and "%" in line:
            parts = line.split()
            coverage_total = parts[-1] if parts else "N/A"

    summary = summary_line or ("Todos los tests pasaron" if ok else "Hay tests fallidos")
    print(f"  {status_icon(ok)} {summary}")
    print(f"  Cobertura total: {coverage_total}")

    return {
        "name": "Pruebas (pytest)",
        "ok": ok,
        "summary": summary,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "coverage": coverage_total,
        "detail": output,
    }


def step_pip_audit() -> dict:
    print_step("6. AUDITORÍA DE DEPENDENCIAS — pip-audit")
    code, stdout, stderr = run(
        ["poetry", "run", "pip-audit", "--format", "json", "--progress-spinner", "off"],
        timeout=120,
    )
    output = stdout + stderr
    vulns_found = []
    total_deps = 0
    skipped_deps = 0
    parse_error = ""

    try:
        data = json.loads(stdout)
        if not isinstance(data, dict) or not isinstance(data.get("dependencies"), list):
            raise ValueError("la salida no contiene una lista 'dependencies'")
        deps = data["dependencies"]
        for dep in deps:
            if not isinstance(dep, dict) or not isinstance(dep.get("vulns", []), list):
                raise ValueError("entrada de dependencia inválida")
            if "skip_reason" in dep:
                skipped_deps += 1
                continue
            total_deps += 1
            for v in dep.get("vulns", []):
                if not isinstance(v, dict):
                    raise ValueError("entrada de vulnerabilidad inválida")
                vulns_found.append(
                    {
                        "package": dep.get("name", "desconocido"),
                        "version": dep.get("version", "desconocida"),
                        "cve": v.get("id", "N/A"),
                        "fix": v.get("fix_versions", []),
                    }
                )
        parse_error = ""
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        parse_error = str(exc)
    if not parse_error and total_deps == 0:
        parse_error = "pip-audit no reportó dependencias auditables"

    # Deduplicar por (package, cve)
    seen = set()
    unique_vulns = []
    for v in vulns_found:
        key = (v["package"], v["cve"])
        if key not in seen:
            seen.add(key)
            unique_vulns.append(v)

    if parse_error:
        audit_ok = False
        summary = f"No se pudo validar la salida de pip-audit: {parse_error}"
    elif unique_vulns:
        audit_ok = False
        summary = (
            f"{total_deps} dependencias auditadas ({skipped_deps} omitidas) — "
            f"{len(unique_vulns)} hallazgos únicos en {len({v['package'] for v in unique_vulns})} paquetes"
        )
    elif code != 0:
        audit_ok = False
        summary = f"pip-audit terminó con código {code}"
    else:
        audit_ok = True
        summary = (
            f"{total_deps} dependencias auditadas ({skipped_deps} omitidas) — "
            "sin vulnerabilidades"
        )
    print(f"  {status_icon(audit_ok)} {summary}")
    for v in unique_vulns:
        fix = v["fix"] if v["fix"] else ["sin fix"]
        print(f"    WARN {v['package']} {v['version']} — {v['cve']} (fix: {fix})")

    return {
        "name": "Auditoría de dependencias (pip-audit)",
        "ok": audit_ok,
        "summary": summary,
        "total_deps": total_deps,
        "skipped_deps": skipped_deps,
        "vulns": unique_vulns,
        "detail": output,
    }


def step_docker() -> dict:
    print_step("7. DOCKER BUILD — imagen multistage")
    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print(f"  {status_icon(False)} Dockerfile no encontrado")
        return {"name": "Docker build", "ok": False, "summary": "Dockerfile no encontrado"}

    print("  Ejecutando docker build (puede tardar)...")
    code, stdout, stderr = run(
        ["docker", "build", "-t", "order-management:validation", "--quiet", "."],
        timeout=600,
    )
    ok = code == 0
    output = stdout + stderr

    image_size = "N/A"
    if ok:
        code2, out2, _ = run(
            ["docker", "image", "inspect", "order-management:validation", "--format", "{{.Size}}"]
        )
        if code2 == 0 and out2.strip():
            try:
                size_mb = int(out2.strip()) / (1024 * 1024)
                image_size = f"{size_mb:.0f} MB"
            except ValueError:
                pass

    summary = f"Build exitoso — imagen: {image_size}" if ok else "Build fallido"
    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Docker build (multistage)",
        "ok": ok,
        "summary": summary,
        "image_size": image_size,
        "detail": output[:500],
    }


def step_alembic() -> dict:
    print_step("8. MIGRACIONES — Alembic")
    code, stdout, stderr = run(["poetry", "run", "alembic", "history"])
    ok = code == 0
    output = stdout + stderr
    lines = [
        line for line in output.strip().splitlines() if line.strip() and not line.startswith("INFO")
    ]
    summary = f"{len(lines)} migraciones en historial" if ok else "Error al leer historial"
    print(f"  {status_icon(ok)} {summary}")
    for line in lines:
        print(f"    {line}")
    return {
        "name": "Migraciones (Alembic)",
        "ok": ok,
        "summary": summary,
        "migrations": lines,
        "detail": output,
    }


def step_wheel() -> dict:
    print_step("9. EMPAQUETADO — wheel")
    dist = Path("dist")
    wheels = list(dist.glob("*.whl")) if dist.exists() else []
    if not wheels:
        # Intentar build
        code, _, _ = run(["poetry", "build", "--format", "wheel"])
        wheels = list(dist.glob("*.whl")) if dist.exists() else []

    ok = len(wheels) > 0
    if ok:
        w = wheels[0]
        size_kb = w.stat().st_size / 1024
        summary = f"{w.name} ({size_kb:.1f} KB)"
    else:
        summary = "No se encontró wheel"

    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "Empaquetado (wheel)",
        "ok": ok,
        "summary": summary,
        "detail": "",
    }


def step_api_health() -> dict:
    print_step("10. API — health check (si está corriendo)")
    try:
        import httpx

        resp = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
        ok = resp.status_code == 200
        summary = f"HTTP {resp.status_code} — {resp.json()}" if ok else f"HTTP {resp.status_code}"
    except Exception as e:
        ok = False
        summary = (
            f"API no disponible en {API_BASE_URL} ({type(e).__name__}) — "
            "levántala con: poetry run uvicorn order_management.api.main:app"
        )

    print(f"  {status_icon(ok)} {summary}")
    return {
        "name": "API health check",
        "ok": ok,
        "summary": summary,
        "detail": "",
    }


# ---------------------------------------------------------------------------
# Generador de reporte Markdown
# ---------------------------------------------------------------------------


def generate_report(results: list[dict], elapsed: float) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")  # noqa: UP017
    total = len(results)
    passed_steps = sum(1 for r in results if r["ok"])
    failed_steps = total - passed_steps

    lines = [
        "# Reporte de Validación — Order Management System",
        "",
        f"**Fecha:** {now}  ",
        f"**Duración total:** {elapsed:.1f} segundos  ",
        f"**Resultado:** {passed_steps}/{total} pasos exitosos  ",
        "",
        "---",
        "",
        "## Resumen ejecutivo",
        "",
        "| # | Paso | Estado | Resultado |",
        "|---|------|--------|-----------|",
    ]

    for i, r in enumerate(results, 1):
        icon = md_icon(r["ok"])
        name = r["name"]
        summary = r.get("summary", "").replace("|", "\\|")
        lines.append(f"| {i} | {name} | {icon} | {summary} |")

    lines += ["", "---", ""]

    # Detalle por sección
    lines.append("## Detalle por sección")
    lines.append("")

    # 1. Calidad de código
    quality_steps = [
        r
        for r in results
        if r["name"]
        in (
            "Tipado estático (mypy)",
            "Linting (ruff)",
            "Formato (black)",
            "Orden de imports (isort)",
        )
    ]
    lines.append("### Calidad de código")
    lines.append("")
    for r in quality_steps:
        icon = md_icon(r["ok"])
        lines.append(f"- {icon} **{r['name']}**: {r.get('summary', '')}")
    lines.append("")

    # 2. Pruebas
    test_r = next((r for r in results if "pytest" in r["name"]), None)
    if test_r:
        lines.append("### Pruebas")
        lines.append("")
        lines.append(f"- {md_icon(test_r['ok'])} **{test_r['name']}**")
        lines.append(f"  - Tests pasados: **{test_r.get('passed', 'N/A')}**")
        lines.append(f"  - Tests fallidos: **{test_r.get('failed', 0)}**")
        lines.append(f"  - Skipped: **{test_r.get('skipped', 0)}**")
        lines.append(f"  - Cobertura total: **{test_r.get('coverage', 'N/A')}**")
        lines.append(f"  - Resumen: `{test_r.get('summary', '')}`")
        lines.append("")

    # 3. Seguridad
    audit_r = next((r for r in results if "pip-audit" in r["name"]), None)
    if audit_r:
        lines.append("### Seguridad — Auditoría de dependencias")
        lines.append("")
        lines.append(f"- {md_icon(audit_r['ok'])} **{audit_r['name']}**")
        lines.append(f"  - {audit_r.get('summary', '')}")
        vulns = audit_r.get("vulns", [])
        if vulns:
            lines.append("")
            lines.append("  | Paquete | Versión | CVE | Fix disponible |")
            lines.append("  |---------|---------|-----|----------------|")
            for v in vulns:
                fix = ", ".join(v["fix"]) if v["fix"] else "No disponible"
                lines.append(f"  | {v['package']} | {v['version']} | {v['cve']} | {fix} |")
        lines.append("")

    # 4. Docker
    docker_r = next((r for r in results if "Docker" in r["name"]), None)
    if docker_r:
        lines.append("### Docker")
        lines.append("")
        lines.append(
            f"- {md_icon(docker_r['ok'])} **{docker_r['name']}**: {docker_r.get('summary', '')}"
        )
        lines.append("")

    # 5. Migraciones
    alembic_r = next((r for r in results if "Alembic" in r["name"]), None)
    if alembic_r:
        lines.append("### Migraciones Alembic")
        lines.append("")
        migrations = alembic_r.get("migrations", [])
        for m in migrations:
            lines.append(f"- `{m}`")
        lines.append("")

    # 6. Empaquetado
    wheel_r = next((r for r in results if "wheel" in r["name"]), None)
    if wheel_r:
        lines.append("### Empaquetado")
        lines.append("")
        lines.append(
            f"- {md_icon(wheel_r['ok'])} **{wheel_r['name']}**: {wheel_r.get('summary', '')}"
        )
        lines.append("")

    # 7. API
    api_r = next((r for r in results if "health" in r["name"]), None)
    if api_r:
        lines.append("### API")
        lines.append("")
        lines.append(f"- {md_icon(api_r['ok'])} **{api_r['name']}**: {api_r.get('summary', '')}")
        lines.append("")

    # Conclusión
    lines += ["---", "", "## Conclusión", ""]
    if failed_steps == 0:
        lines.append("**El proyecto supera todos los criterios de calidad y entrega.**  ")
        lines.append("Listo para presentación.")
    else:
        lines.append(f"**{failed_steps} paso(s) requieren atención** antes de la entrega final.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Reporte generado automáticamente por `scripts/run_full_validation.py`_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 65)
    print("  VALIDACIÓN COMPLETA — Order Management System")
    print("  Proyecto Final Integrador")
    print("=" * 65)

    start = time.perf_counter()
    results: list[dict] = []

    steps = [
        step_mypy,
        step_ruff,
        step_black,
        step_isort,
        step_pytest,
        step_pip_audit,
        step_docker,
        step_alembic,
        step_wheel,
        step_api_health,
    ]

    for step_fn in steps:
        try:
            result = step_fn()
        except subprocess.TimeoutExpired:
            result = {
                "name": step_fn.__name__.replace("step_", ""),
                "ok": False,
                "summary": "Timeout — el paso tardó demasiado",
            }
        except Exception as exc:
            result = {
                "name": step_fn.__name__.replace("step_", ""),
                "ok": False,
                "summary": f"Error inesperado: {exc}",
            }
        results.append(result)

    elapsed = time.perf_counter() - start

    # Generar y guardar reporte
    print_step("GENERANDO REPORTE MARKDOWN")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_md = generate_report(results, elapsed)
    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"Reporte guardado en: {REPORT_PATH.resolve()}")

    # Resumen final en consola
    print("\n" + "=" * 65)
    print("  RESUMEN FINAL")
    print("=" * 65)
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    for r in results:
        icon = status_icon(r["ok"])
        print(f"  {icon}  {r['name']:<40} {r.get('summary', '')[:30]}")

    print(f"\n  Resultado: {passed}/{len(results)} pasos exitosos")
    print(f"  Duración:  {elapsed:.1f} segundos")
    print(f"  Reporte:   {REPORT_PATH}")
    print("=" * 65 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
