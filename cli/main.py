#!/usr/bin/env python3
import typer
import httpx
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(help="AI Audit Logger — query and monitor your LLM call logs")
console = Console()

DEFAULT_SERVER = "http://localhost:8000"


@app.callback()
def main(
    ctx: typer.Context,
    server: str = typer.Option(DEFAULT_SERVER, "--server", "-s", envvar="AUDIT_SERVER_URL", help="Server URL"),
):
    ctx.ensure_object(dict)
    ctx.obj["server"] = server


@app.command()
def tail(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    user_id: Optional[str] = typer.Option(None, "--user", "-u"),
    app_name: Optional[str] = typer.Option(None, "--app", "-a"),
    session_id: Optional[str] = typer.Option(None, "--session"),
):
    """Show recent log entries."""
    server = ctx.obj["server"]
    params = {"limit": limit}
    if provider:
        params["provider"] = provider
    if model:
        params["model"] = model
    if user_id:
        params["user_id"] = user_id
    if app_name:
        params["app_name"] = app_name
    if session_id:
        params["session_id"] = session_id

    try:
        r = httpx.get(f"{server}/api/v1/logs", params=params)
        r.raise_for_status()
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to server at {server}[/red]")
        raise typer.Exit(1)

    data = r.json()
    entries = data["entries"]

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Timestamp", style="dim", width=19)
    table.add_column("Provider", width=10)
    table.add_column("Model", width=28)
    table.add_column("Tokens", width=12)
    table.add_column("Cost", width=12)
    table.add_column("Latency", width=9)
    table.add_column("Status", width=8)

    for e in entries:
        ts = e["timestamp"][:19].replace("T", " ")
        cost = f"${e['cost_usd']:.5f}" if e.get("cost_usd") else "n/a"
        latency = f"{e['latency_ms']:.0f}ms" if e.get("latency_ms") else "n/a"
        tokens = f"{e.get('tokens_in') or 0}→{e.get('tokens_out') or 0}"
        status = "[red]ERROR[/red]" if e.get("error") else "[green]OK[/green]"
        table.add_row(ts, e["provider"], e["model"], tokens, cost, latency, status)

    console.print(f"\nShowing [bold]{len(entries)}[/bold] of [bold]{data['total']}[/bold] entries\n")
    console.print(table)


@app.command()
def stats(ctx: typer.Context):
    """Show aggregated usage statistics."""
    server = ctx.obj["server"]

    try:
        r = httpx.get(f"{server}/api/v1/logs/stats")
        r.raise_for_status()
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to server at {server}[/red]")
        raise typer.Exit(1)

    data = r.json()

    console.print("\n[bold cyan]AI Audit Logger — Stats[/bold cyan]\n")
    console.print(f"  Total calls:       [bold]{data['total_calls']:,}[/bold]")
    console.print(f"  Total cost:        [bold green]${data['total_cost_usd']:.4f}[/bold green]")
    console.print(f"  Tokens in:         {data['total_tokens_in']:,}")
    console.print(f"  Tokens out:        {data['total_tokens_out']:,}")
    console.print(f"  Avg latency:       {data['avg_latency_ms']:.0f}ms")

    if data["by_model"]:
        console.print("\n  [bold]By model:[/bold]")
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Model", width=35)
        table.add_column("Calls", justify="right", width=8)
        table.add_column("Cost (USD)", justify="right", width=12)
        for m in data["by_model"]:
            table.add_row(m["model"], str(m["calls"]), f"${m['cost_usd']:.4f}")
        console.print(table)
    console.print()


@app.command()
def get(ctx: typer.Context, entry_id: str = typer.Argument(..., help="Log entry ID")):
    """Show full detail for a single log entry."""
    server = ctx.obj["server"]

    try:
        r = httpx.get(f"{server}/api/v1/logs", params={"limit": 1})
        r.raise_for_status()
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to server at {server}[/red]")
        raise typer.Exit(1)

    # Search within recent logs for the ID
    r = httpx.get(f"{server}/api/v1/logs", params={"limit": 500})
    entries = r.json()["entries"]
    entry = next((e for e in entries if e["id"].startswith(entry_id)), None)

    if not entry:
        console.print(f"[red]Entry {entry_id} not found[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]Entry {entry['id']}[/bold cyan]")
    for k, v in entry.items():
        if v is not None:
            console.print(f"  [bold]{k}:[/bold] {v}")
    console.print()


if __name__ == "__main__":
    app()
