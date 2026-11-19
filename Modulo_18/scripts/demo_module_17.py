"""
Demo del Módulo 17: Empaquetado, distribución y CI/CD
Demuestra localmente:
  1. Generar wheel con poetry build
  2. Verificar el contenido del wheel
  3. Build de la imagen Docker multistage
  4. Levantar el contenedor y verificar el health check
  5. Resumen del pipeline CI/CD
"""

import shutil
import subprocess
import time
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: str | None = None, capture: bool = True) -> tuple[int, str, str]:
    """Ejecuta un comando y retorna (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _print_section(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"{title}")
    print("=" * 65)


def _check(label: str, condition: bool, detail: str = "") -> None:
    icon = "✓" if condition else "✗"
    line = f"  {icon} {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    if not condition:
        print("    ⚠ Fallo detectado")


# ---------------------------------------------------------------------------
# PARTE 1 — Generar wheel
# ---------------------------------------------------------------------------


def demo_wheel() -> Path | None:
    _print_section("1. GENERAR WHEEL — poetry build")

    dist_dir = Path("dist")

    # Limpiar dist anterior
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("  Limpiado directorio dist/ anterior")

    print("\n  Ejecutando: poetry build ...")
    code, stdout, stderr = _run(["poetry", "build"])

    if code != 0:
        print(f"  ✗ Error en poetry build:\n{stderr}")
        return None

    # Buscar el wheel generado
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))

    _check("poetry build exitoso", code == 0)
    _check("Wheel generado (.whl)", len(wheels) > 0, wheels[0].name if wheels else "no encontrado")
    _check(
        "Sdist generado (.tar.gz)", len(sdists) > 0, sdists[0].name if sdists else "no encontrado"
    )

    if wheels:
        print("\n  Artefactos en dist/:")
        for f in sorted(dist_dir.iterdir()):
            print(f"    {f.name:<50} {f.stat().st_size / 1024:>8.1f} KB")
        return wheels[0]

    return None


# ---------------------------------------------------------------------------
# PARTE 2 — Inspeccionar el wheel
# ---------------------------------------------------------------------------


def demo_inspect_wheel(wheel_path: Path) -> None:
    _print_section("2. INSPECCIONAR WHEEL")

    print(f"\n  Archivo: {wheel_path.name}")
    print("  Un wheel es un ZIP con extensión .whl\n")

    with zipfile.ZipFile(wheel_path) as zf:
        all_files = zf.namelist()

    # Agrupar por categoría
    py_files = [f for f in all_files if f.endswith(".py")]
    metadata = [f for f in all_files if "METADATA" in f or "RECORD" in f]
    typed = [f for f in all_files if "py.typed" in f]

    print(f"  Total de archivos en el wheel : {len(all_files)}")
    print(f"  Archivos .py                  : {len(py_files)}")
    print(f"  Marcador py.typed             : {'Sí ✓' if typed else 'No ✗'}")

    print("\n  Estructura del paquete (primeros 15 archivos):")
    for f in sorted(all_files)[:15]:
        print(f"    {f}")
    if len(all_files) > 15:
        print(f"    ... ({len(all_files) - 15} archivos más)")

    print("\n  Metadata:")
    with zipfile.ZipFile(wheel_path) as zf:
        for f in metadata:
            if "METADATA" in f and not f.endswith("RECORD"):
                content = zf.read(f).decode("utf-8")
                for line in content.split("\n")[:8]:
                    if line.strip():
                        print(f"    {line}")
                break


# ---------------------------------------------------------------------------
# PARTE 3 — Docker build
# ---------------------------------------------------------------------------


def demo_docker_build() -> bool:
    _print_section("3. DOCKER BUILD — imagen multistage")

    # Verificar que Docker está disponible
    code, stdout, _ = _run(["docker", "--version"])
    if code != 0:
        print("  ✗ Docker no está disponible")
        return False

    docker_version = stdout.strip()
    print(f"\n  {docker_version}")

    # Verificar que existe el Dockerfile
    dockerfile = Path("Dockerfile")
    _check("Dockerfile existe", dockerfile.exists())
    if not dockerfile.exists():
        return False

    print("\n  Ejecutando: docker build -t order-management:demo ...")
    print("  (esto puede tardar 2-5 minutos la primera vez)\n")

    # Build con output visible
    build_process = subprocess.run(
        ["docker", "build", "-t", "order-management:demo", "--progress=plain", "."],
        capture_output=False,
        text=True,
    )

    success = build_process.returncode == 0
    _check("docker build exitoso", success)

    if success:
        # Obtener tamaño de la imagen
        code, stdout, _ = _run(
            ["docker", "image", "inspect", "order-management:demo", "--format", "{{.Size}}"]
        )
        if code == 0:
            size_mb = int(stdout.strip()) / (1024 * 1024)
            print(f"  Tamaño de la imagen: {size_mb:.0f} MB")

    return success


# ---------------------------------------------------------------------------
# PARTE 4 — Levantar contenedor y verificar API
# ---------------------------------------------------------------------------


def demo_docker_run() -> None:
    _print_section("4. DOCKER RUN — verificar API en contenedor")

    container_name = "order-management-demo"

    # Limpiar contenedor anterior si existe
    _run(["docker", "rm", "-f", container_name])

    print(f"\n  Levantando contenedor '{container_name}'...")
    code, _, stderr = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            "8001:8000",
            "-e",
            "DATABASE_URL=sqlite:////app/data/orders_demo.db",
            "order-management:demo",
        ]
    )

    _check("Contenedor iniciado", code == 0)
    if code != 0:
        print(f"  Error: {stderr}")
        return

    # Esperar a que la API esté lista
    print("  Esperando a que la API esté lista", end="", flush=True)
    import httpx

    ready = False
    for _ in range(20):
        time.sleep(1)
        print(".", end="", flush=True)
        try:
            resp = httpx.get("http://localhost:8001/health", timeout=2.0)
            if resp.status_code == 200:
                ready = True
                break
        except httpx.RequestError:
            continue
    print()

    _check("API responde en /health", ready)

    if ready:
        try:
            resp = httpx.get("http://localhost:8001/health", timeout=5.0)
            data = resp.json()
            print(f"  Respuesta: {data}")

            # Verificar docs
            resp_docs = httpx.get("http://localhost:8001/docs", timeout=5.0)
            _check("Swagger UI disponible en /docs", resp_docs.status_code == 200)

        except httpx.RequestError as e:
            print(f"  Error al consultar la API: {e}")

    # Mostrar logs del contenedor
    code, logs, _ = _run(["docker", "logs", "--tail", "10", container_name])
    if logs.strip():
        print("\n  Últimas líneas del log:")
        for line in logs.strip().split("\n")[-5:]:
            print(f"    {line}")

    # Limpiar
    _run(["docker", "stop", container_name])
    _run(["docker", "rm", container_name])
    print("\n  Contenedor detenido y eliminado")


# ---------------------------------------------------------------------------
# PARTE 5 — Resumen del pipeline CI/CD
# ---------------------------------------------------------------------------


def demo_pipeline_summary() -> None:
    _print_section("5. PIPELINE CI/CD — GitHub Actions")

    ci_file = Path(".github") / "workflows" / "ci.yml"
    _check("ci.yml creado", ci_file.exists(), str(ci_file))

    print(
        """
  Flujo del pipeline:

  push/PR a main o develop
        │
        ▼
  ┌─────────────┐
  │   lint      │  ruff · black · isort
  └──────┬──────┘
         │
  ┌──────┴──────────────┐
  │                     │
  ▼                     ▼
  ┌─────────────┐  ┌─────────────┐
  │  typecheck  │  │    test     │
  │   (mypy)    │  │  (pytest)   │
  └──────┬──────┘  └──────┬──────┘
         │                │
         └───────┬─────────┘
                 ▼
         ┌─────────────┐
         │    build    │  poetry build → wheel + sdist
         └──────┬──────┘
                │
                ▼  (solo push a main)
         ┌─────────────┐
         │   docker    │  build + push → ghcr.io
         └─────────────┘

  Jobs configurados:
    lint       → siempre
    typecheck  → después de lint
    test       → después de lint (paralelo con typecheck)
    build      → después de typecheck + test
    docker     → después de build, solo en push a main

  Registry: ghcr.io/{github.repository}
  Tags:     latest · branch-name · sha-{commit}
    """
    )

    # Verificar si hay commits pendientes
    code, stdout, _ = _run(["git", "status", "--short"])
    if stdout.strip():
        print("  Archivos pendientes de commit:")
        for line in stdout.strip().split("\n"):
            print(f"    {line}")
    else:
        print("  ✓ Repositorio limpio")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n" + "=" * 65)
    print("MÓDULO 17: EMPAQUETADO, DISTRIBUCIÓN Y CI/CD")
    print("wheel · Docker multistage · GitHub Actions")
    print("=" * 65)

    # 1. Generar wheel
    wheel_path = demo_wheel()

    # 2. Inspeccionar wheel
    if wheel_path and wheel_path.exists():
        demo_inspect_wheel(wheel_path)
    else:
        print("\n  ⚠ Saltando inspección — wheel no generado")

    # 3. Docker build
    build_ok = demo_docker_build()

    # 4. Docker run (solo si el build fue exitoso)
    if build_ok:
        demo_docker_run()
    else:
        print("\n  ⚠ Saltando docker run — build falló")

    # 5. Resumen del pipeline
    demo_pipeline_summary()

    print("\n" + "=" * 65)
    print("✓ DEMO MÓDULO 17 COMPLETADO")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
