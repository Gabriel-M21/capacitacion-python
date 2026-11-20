"""
Comandos de órdenes - Módulo 18: CLI y automatización
CRUD completo consumiendo la API REST.
"""

import json
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

from order_management.cli.config import config

app = typer.Typer(help="Gestión de órdenes de compra")
console = Console()


def _require_auth() -> dict[str, str]:
    """Verifica que hay un token activo. Sale con error si no lo hay."""
    headers = config.auth_headers()
    if not headers:
        typer.secho(
            "✗ No autenticado. Ejecuta primero: orders-cli auth login",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    return headers


def _handle_error(e: Exception) -> None:
    """Maneja errores HTTP y de red de forma uniforme."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 401:
            typer.secho("✗ Token expirado o inválido. Vuelve a hacer login.", fg=typer.colors.RED)
        elif status == 404:
            typer.secho("✗ Recurso no encontrado.", fg=typer.colors.RED)
        elif status == 422:
            detail = e.response.json().get("detail", "Datos inválidos")
            typer.secho(f"✗ Datos inválidos: {detail}", fg=typer.colors.RED)
        else:
            typer.secho(f"✗ Error HTTP {status}", fg=typer.colors.RED)
    elif isinstance(e, httpx.RequestError):
        typer.secho(f"✗ No se pudo conectar a {config.api_url}", fg=typer.colors.RED)
    else:
        typer.secho(f"✗ Error inesperado: {e}", fg=typer.colors.RED)
    raise typer.Exit(1)


def _print_order(order: dict[str, Any]) -> None:
    """Imprime una orden con formato Rich."""
    console.rule(f"[bold cyan]{order['order_id']}")

    console.print(
        f"  [bold]Cliente:[/bold] {order['customer']['name']} " f"<{order['customer']['email']}>"
    )
    console.print(f"  [bold]Estado:[/bold]  {order['status']}")
    console.print(f"  [bold]Total:[/bold]   ${float(order['total']):.2f}")
    console.print(f"  [bold]Items:[/bold]   {order['item_count']}")

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
    table.add_column("Producto", style="cyan", width=35)
    table.add_column("Cantidad", justify="right")
    table.add_column("Precio", justify="right")
    table.add_column("Subtotal", justify="right")

    for item in order.get("items", []):
        table.add_row(
            item["product_name"],
            str(item["quantity"]),
            f"${float(item['unit_price']):.2f}",
            f"${float(item['subtotal']):.2f}",
        )

    console.print(table)
    if order.get("notes"):
        console.print(f"  [bold]Notas:[/bold] {order['notes']}")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_orders(
    status: str = typer.Option(None, "--status", "-s", help="Filtrar por estado"),
    limit: int = typer.Option(20, "--limit", "-l", help="Máximo de órdenes a mostrar"),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
) -> None:
    """Lista todas las órdenes. Opcionalmente filtra por estado."""
    headers = _require_auth()
    try:
        response = httpx.get(
            f"{config.api_url}/orders",
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
        orders: list[dict[str, Any]] = response.json()

        if status:
            orders = [o for o in orders if o["status"] == status]

        orders = orders[:limit]

        if json_output:
            typer.echo(json.dumps(orders, indent=2, ensure_ascii=False))
            return

        if not orders:
            typer.secho("No hay órdenes que mostrar.", fg=typer.colors.YELLOW)
            return

        table = Table(
            title=f"Órdenes ({len(orders)})",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("ID", style="cyan", width=12)
        table.add_column("Cliente", width=22)
        table.add_column("Estado", width=12)
        table.add_column("Total", justify="right", width=10)
        table.add_column("Items", justify="right", width=6)

        STATUS_COLOR = {
            "pending": "yellow",
            "confirmed": "blue",
            "shipped": "cyan",
            "delivered": "green",
            "cancelled": "red",
        }

        for order in orders:
            color = STATUS_COLOR.get(order["status"], "white")
            status_text = f"[{color}]{order['status']}[/{color}]"
            table.add_row(
                order["order_id"],
                order["customer"]["name"][:22],
                status_text,
                f"${float(order['total']):.2f}",
                str(order["item_count"]),
            )

        console.print(table)

    except Exception as e:
        _handle_error(e)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


@app.command()
def get(
    order_id: str = typer.Argument(..., help="ID de la orden (ej. ORD-00001)"),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
) -> None:
    """Muestra el detalle de una orden específica."""
    headers = _require_auth()
    try:
        response = httpx.get(
            f"{config.api_url}/orders/{order_id}",
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
        order = response.json()

        if json_output:
            typer.echo(json.dumps(order, indent=2, ensure_ascii=False))
        else:
            _print_order(order)

    except Exception as e:
        _handle_error(e)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@app.command()
def create(
    customer_name: str = typer.Option(..., "--name", "-n", prompt="Nombre del cliente"),
    customer_email: str = typer.Option(..., "--email", "-e", prompt="Email del cliente"),
    customer_phone: str = typer.Option(None, "--phone", "-p", help="Teléfono (opcional)"),
    notes: str = typer.Option(None, "--notes", help="Notas adicionales"),
) -> None:
    """
    Crea una nueva orden de forma interactiva.
    Te pedirá los items uno a uno hasta que presiones Enter sin producto.
    """
    headers = _require_auth()

    # Recopilar items interactivamente
    items: list[dict[str, Any]] = []
    typer.echo("\nAgrega items (Enter vacío para terminar):")

    while True:
        product = typer.prompt("  Producto", default="", show_default=False)
        if not product.strip():
            if not items:
                typer.secho("  Debes agregar al menos un item.", fg=typer.colors.YELLOW)
                continue
            break

        quantity = typer.prompt("  Cantidad", default=1, type=int)
        price = typer.prompt("  Precio unitario", type=float)

        items.append(
            {
                "product_name": product,
                "quantity": quantity,
                "unit_price": price,
            }
        )
        typer.secho(
            f"  ✓ Item agregado: {product} x{quantity} @ ${price:.2f}", fg=typer.colors.GREEN
        )

    payload: dict[str, Any] = {
        "customer": {
            "name": customer_name,
            "email": customer_email,
        },
        "items": items,
    }
    if customer_phone:
        payload["customer"]["phone"] = customer_phone
    if notes:
        payload["notes"] = notes

    # Confirmación
    total = sum(i["quantity"] * i["unit_price"] for i in items)
    typer.echo(f"\n  Resumen: {len(items)} items — Total estimado: ${total:.2f}")
    if not typer.confirm("¿Confirmar creación?"):
        typer.secho("Cancelado.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    try:
        response = httpx.post(
            f"{config.api_url}/orders",
            json=payload,
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
        order = response.json()
        typer.secho(f"\n✓ Orden creada: {order['order_id']}", fg=typer.colors.GREEN)
        _print_order(order)

    except Exception as e:
        _handle_error(e)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@app.command()
def delete(
    order_id: str = typer.Argument(..., help="ID de la orden a eliminar"),
    force: bool = typer.Option(False, "--force", "-f", help="No pedir confirmación"),
) -> None:
    """Elimina una orden permanentemente."""
    headers = _require_auth()

    if not force:
        typer.secho(
            f"⚠ Esto eliminará la orden {order_id} permanentemente.", fg=typer.colors.YELLOW
        )
        if not typer.confirm("¿Estás seguro?"):
            typer.secho("Cancelado.", fg=typer.colors.YELLOW)
            raise typer.Exit(0)

    try:
        response = httpx.delete(
            f"{config.api_url}/orders/{order_id}",
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
        typer.secho(f"✓ Orden {order_id} eliminada.", fg=typer.colors.GREEN)

    except Exception as e:
        _handle_error(e)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    order_id: str = typer.Argument(..., help="ID de la orden"),
    new_status: str = typer.Argument(
        ..., help="Nuevo estado: confirmed|shipped|delivered|cancelled"
    ),
) -> None:
    """Cambia el estado de una orden."""
    valid = {"confirmed", "shipped", "delivered", "cancelled", "processing"}
    if new_status not in valid:
        typer.secho(
            f"✗ Estado inválido: '{new_status}'. Válidos: {', '.join(sorted(valid))}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    headers = _require_auth()
    try:
        response = httpx.patch(
            f"{config.api_url}/orders/{order_id}/status",
            json={"status": new_status},
            headers=headers,
            timeout=config.timeout,
        )
        response.raise_for_status()
        order = response.json()
        typer.secho(
            f"✓ Orden {order_id} → estado: {order['status']}",
            fg=typer.colors.GREEN,
        )

    except Exception as e:
        _handle_error(e)
