"""
CLI principal - Módulo 18: CLI y automatización
Entry point de la aplicación de línea de comandos.
"""

import typer

from order_management.cli import auth, orders
from order_management.cli.config import config

app = typer.Typer(
    name="orders-cli",
    help="CLI para gestionar órdenes de compra vía API REST.",
    add_completion=True,
    rich_markup_mode="rich",
)

# Registrar sub-aplicaciones
app.add_typer(auth.app, name="auth", help="Autenticación (login/logout/whoami)")
app.add_typer(orders.app, name="orders", help="Gestión de órdenes (list/get/create/delete/status)")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Muestra la versión"),
    api_url: str = typer.Option(None, "--api-url", help="URL base de la API"),
) -> None:
    """
    [bold cyan]orders-cli[/bold cyan] — Gestión de órdenes desde la terminal.

    [bold]Inicio rápido:[/bold]
      orders-cli auth login
      orders-cli orders list
      orders-cli orders get ORD-00001
    """
    if version:
        typer.echo("orders-cli v0.1.0")
        raise typer.Exit()

    if api_url:
        import os

        os.environ["ORDERS_API_URL"] = api_url

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def info() -> None:
    """Muestra la configuración actual de la CLI."""
    typer.echo("\n[bold]Configuración actual:[/bold]")
    typer.echo(f"  API URL     : {config.api_url}")
    typer.echo(f"  Timeout     : {config.timeout}s")
    typer.echo(f"  Token file  : {config.token_file}")

    token = config.load_token()
    if token:
        typer.secho(f"  Sesión      : activa (token: {token[:20]}...)", fg=typer.colors.GREEN)
    else:
        typer.secho("  Sesión      : no autenticado", fg=typer.colors.YELLOW)


if __name__ == "__main__":
    app()
