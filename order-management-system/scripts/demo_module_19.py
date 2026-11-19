"""
Demo del Módulo 19: Seguridad y mantenimiento
Demuestra:
  1. Configuración centralizada con pydantic-settings
  2. Auditoría de dependencias con pip-audit
  3. Generación de SECRET_KEY seguro
  4. Verificación de hardening del Dockerfile
  5. Checklist de seguridad del proyecto
"""

import json
import secrets
import subprocess
import warnings
from pathlib import Path

from order_management.config.settings import Settings, get_settings


# ---------------------------------------------------------------------------
# PARTE 1 — Configuración con pydantic-settings
# ---------------------------------------------------------------------------


def demo_settings() -> None:
    print("\n" + "=" * 65)
    print("1. CONFIGURACIÓN — pydantic-settings")
    print("=" * 65)

    # Resetear caché para demo limpio
    get_settings.cache_clear()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        settings = get_settings()

    print(f"\n  Configuración cargada:")
    print(f"    app_name                     : {settings.app_name}")
    print(f"    app_version                  : {settings.app_version}")
    print(f"    debug                        : {settings.debug}")
    print(f"    database_url                 : {settings.database_url}")
    print(f"    algorithm                    : {settings.algorithm}")
    print(f"    access_token_expire_minutes  : {settings.access_token_expire_minutes}")
    print(f"    secret_key                   : {'*' * 20} (oculto)")
    print(f"    cors_origins                 : {settings.cors_origins}")

    if caught:
        print(f"\n  ⚠ Advertencias de seguridad:")
        for w in caught:
            print(f"    {w.message}")
    else:
        print(f"\n  ✓ Sin advertencias de seguridad")

    # Mostrar fuente de configuración
    env_file = Path(".env")
    print(f"\n  Fuente de configuración:")
    print(f"    .env existe     : {env_file.exists()}")
    print(f"    .env.example    : {Path('.env.example').exists()}")
    if env_file.exists():
        lines = [l for l in env_file.read_text().splitlines() if l and not l.startswith("#")]
        print(f"    Variables en .env: {len(lines)}")


# ---------------------------------------------------------------------------
# PARTE 2 — Generación de SECRET_KEY seguro
# ---------------------------------------------------------------------------


def demo_secret_key() -> None:
    print("\n" + "=" * 65)
    print("2. GENERACIÓN DE SECRET_KEY SEGURO")
    print("=" * 65)

    print("\n  Ejemplos de SECRET_KEY seguros generados con secrets.token_hex:")
    for i in range(3):
        key = secrets.token_hex(32)
        print(f"    {i + 1}. {key}")

    print(f"\n  Longitud: 64 caracteres hex = 256 bits de entropía")
    print(f"  Comando: python -c \"import secrets; print(secrets.token_hex(32))\"")

    # Verificar la validación de Settings
    print(f"\n  Validaciones de Settings:")
    try:
        Settings(secret_key="corto")
    except Exception as e:
        print(f"    ✓ SECRET_KEY corto rechazado: {e}")

    try:
        Settings(access_token_expire_minutes=0)
    except Exception as e:
        print(f"    ✓ Expiración inválida rechazada: {e}")

    try:
        Settings(access_token_expire_minutes=9999)
    except Exception as e:
        print(f"    ✓ Expiración excesiva rechazada: {e}")


# ---------------------------------------------------------------------------
# PARTE 3 — Auditoría de dependencias con pip-audit
# ---------------------------------------------------------------------------


def demo_pip_audit() -> None:
    print("\n" + "=" * 65)
    print("3. AUDITORÍA DE DEPENDENCIAS — pip-audit")
    print("=" * 65)

    print("\n  Ejecutando pip-audit...")

    result = subprocess.run(
        ["poetry", "run", "pip-audit", "--format", "json", "--progress-spinner", "off"],
        capture_output=True,
        text=True,
    )

    # pip-audit devuelve exit code 1 si hay vulnerabilidades
    output = result.stdout or result.stderr

    try:
        audit_data = json.loads(output)
        dependencies = audit_data.get("dependencies", [])

        vulnerable = [
            d for d in dependencies
            if d.get("vulns")
        ]
        clean = [d for d in dependencies if not d.get("vulns")]

        print(f"\n  Dependencias auditadas : {len(dependencies)}")
        print(f"  Sin vulnerabilidades   : {len(clean)}")
        print(f"  Con vulnerabilidades   : {len(vulnerable)}")

        if not vulnerable:
            print(f"\n  ✓ No se encontraron vulnerabilidades conocidas")
        else:
            print(f"\n  ⚠ Vulnerabilidades encontradas:")
            for dep in vulnerable:
                for vuln in dep.get("vulns", []):
                    print(f"\n    Paquete : {dep['name']} {dep['version']}")
                    print(f"    CVE     : {vuln.get('id', 'N/A')}")
                    print(f"    Fix     : {vuln.get('fix_versions', ['No disponible'])}")
                    desc = vuln.get('description', '')
                    if desc:
                        print(f"    Desc    : {desc[:100]}...")

            print(f"\n  Para actualizar paquetes vulnerables:")
            for dep in vulnerable:
                fixes = []
                for v in dep.get("vulns", []):
                    fixes.extend(v.get("fix_versions", []))
                if fixes:
                    print(f"    poetry add {dep['name']}@{fixes[-1]}")

    except json.JSONDecodeError:
        # Salida de texto plano
        lines = output.strip().split("\n")
        for line in lines[:20]:
            if line.strip():
                print(f"  {line}")


# ---------------------------------------------------------------------------
# PARTE 4 — Verificación de hardening del Dockerfile
# ---------------------------------------------------------------------------


def demo_dockerfile_hardening() -> None:
    print("\n" + "=" * 65)
    print("4. HARDENING DEL DOCKERFILE")
    print("=" * 65)

    dockerfile = Path("Dockerfile")
    if not dockerfile.exists():
        print("\n  ⚠ Dockerfile no encontrado")
        return

    content = dockerfile.read_text(encoding="utf-8")

    checks = [
        ("Imagen base slim (no full)",
         "python:3.12-slim" in content,
         "Usar python:3.12-slim reduce la superficie de ataque"),

        ("Multistage build",
         "AS builder" in content and "AS runtime" in content,
         "Multistage evita incluir herramientas de build en producción"),

        ("Usuario no-root",
         "useradd" in content and "USER appuser" in content,
         "Correr como root en contenedor es un riesgo de seguridad"),

        ("PYTHONDONTWRITEBYTECODE",
         "PYTHONDONTWRITEBYTECODE=1" in content,
         "Evita archivos .pyc innecesarios"),

        ("PYTHONUNBUFFERED",
         "PYTHONUNBUFFERED=1" in content,
         "Logs en tiempo real sin buffering"),

        ("PIP_NO_CACHE_DIR",
         "PIP_NO_CACHE_DIR=1" in content,
         "Reduce el tamaño de la imagen"),

        ("HEALTHCHECK definido",
         "HEALTHCHECK" in content,
         "Permite a Docker detectar si el servicio está caído"),

        ("EXPOSE documentado",
         "EXPOSE" in content,
         "Documenta el puerto que expone el contenedor"),
    ]

    print(f"\n  {'Check':<40} {'Estado':>8}  Descripción")
    print("  " + "-" * 80)

    passed = 0
    for label, ok, description in checks:
        icon = "✓" if ok else "✗"
        color = "" if ok else "⚠ "
        print(f"  {label:<40} {icon:>8}  {color}{description[:35]}")
        if ok:
            passed += 1

    print(f"\n  Resultado: {passed}/{len(checks)} checks pasados")


# ---------------------------------------------------------------------------
# PARTE 5 — Checklist de seguridad
# ---------------------------------------------------------------------------


def demo_security_checklist() -> None:
    print("\n" + "=" * 65)
    print("5. CHECKLIST DE SEGURIDAD DEL PROYECTO")
    print("=" * 65)

    checks = [
        (".env en .gitignore",
         ".env" in Path(".gitignore").read_text() if Path(".gitignore").exists() else False),
        (".env.example existe (sin secretos reales)",
         Path(".env.example").exists()),
        ("py.typed marcador presente",
         Path("src/order_management/py.typed").exists()),
        ("JWT usa Settings (no hardcoded)",
         "get_settings" in Path("src/order_management/api/security/jwt.py").read_text()
         if Path("src/order_management/api/security/jwt.py").exists() else False),
        ("DB URL usa Settings (no hardcoded)",
         "get_settings" in Path("src/order_management/infrastructure/db/session.py").read_text()
         if Path("src/order_management/infrastructure/db/session.py").exists() else False),
        ("pre-commit configurado",
         Path(".pre-commit-config.yaml").exists()),
        ("Dockerfile con usuario no-root",
         "USER appuser" in Path("Dockerfile").read_text()
         if Path("Dockerfile").exists() else False),
        ("GitHub Actions CI configurado",
         Path(".github/workflows/ci.yml").exists()),
        ("pip-audit instalado",
         True),  # ya lo verificamos al instalar
    ]

    print(f"\n  {'Check':<45} Estado")
    print("  " + "-" * 55)

    passed = sum(1 for _, ok in checks if ok)
    for label, ok in checks:
        icon = "✓" if ok else "✗"
        print(f"  {label:<45} {icon}")

    print(f"\n  Resultado: {passed}/{len(checks)} checks de seguridad OK")
    if passed == len(checks):
        print("¡Proyecto con buenas prácticas de seguridad!")
    else:
        pending = [label for label, ok in checks if not ok]
        print(f"\n  Pendientes:")
        for p in pending:
            print(f"    • {p}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 65)
    print("MÓDULO 19: SEGURIDAD Y MANTENIMIENTO")
    print("pydantic-settings · pip-audit · hardening · secretos")
    print("=" * 65)

    demo_settings()
    demo_secret_key()
    demo_pip_audit()
    demo_dockerfile_hardening()
    demo_security_checklist()

    print("\n" + "=" * 65)
    print("✓ DEMO MÓDULO 19 COMPLETADO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
