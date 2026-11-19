"""
Comandos de autenticación - Módulo 18: CLI y automatización
"""

import httpx
import typer

from order_management.cli.config import config

app = typer.Typer(help="Autenticación con la API de órdenes")


@app.command()
def login(
    username: str = typer.Option(
        ...,
        "--username", "-u",
        prompt="Email",
        help="Email del usuario",
    ),
    password: str = typer.Option(
        ...,
        "--password", "-p",
        prompt="Contraseña",
        hide_input=True,
        help="Contraseña del usuario",
    ),
) -> None:
    """
    Inicia sesión y guarda el token JWT localmente.

    Credenciales de prueba:
      admin@example.com / admin123
      user@example.com  / user123
    """
    try:
        response = httpx.post(
            f"{config.api_url}/auth/login",
            data={"username": username, "password": password},
            timeout=config.timeout,
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        config.save_token(token)
        typer.secho(f"✓ Sesión iniciada como {username}", fg=typer.colors.GREEN)
        typer.echo(f"  Token guardado en: {config.token_file}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            typer.secho("✗ Credenciales incorrectas", fg=typer.colors.RED)
        else:
            typer.secho(f"✗ Error HTTP {e.response.status_code}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except httpx.RequestError as e:
        typer.secho(f"✗ No se pudo conectar a {config.api_url}: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def logout() -> None:
    """Elimina el token JWT guardado localmente."""
    config.clear_token()
    typer.secho("✓ Sesión cerrada", fg=typer.colors.GREEN)


@app.command()
def whoami() -> None:
    """Muestra si hay una sesión activa."""
    token = config.load_token()
    if token:
        typer.secho("✓ Sesión activa", fg=typer.colors.GREEN)
        typer.echo(f"  Token: {token[:20]}...")
        typer.echo(f"  Archivo: {config.token_file}")
    else:
        typer.secho("✗ No hay sesión activa. Usa: orders-cli auth login", fg=typer.colors.YELLOW)
