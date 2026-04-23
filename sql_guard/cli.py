from __future__ import annotations

import importlib.resources
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="sql-guard",
    help="Trust and observability layer for text-to-SQL chatbots.",
    add_completion=False,
)
console = Console()


def _load_guard(config_path: Optional[Path]):
    from sql_guard.config import load_config

    cfg = load_config(config_path)
    # CLI ask/verify require a backend — prompt user to configure one.
    # For standalone verify we create a no-op backend.
    from sql_guard.backends.custom import CustomBackend

    def _noop(q: str):
        raise RuntimeError(
            "No backend configured. Use Guard() in Python to set a backend."
        )

    backend = CustomBackend(fn=_noop, name="cli-noop")
    from sql_guard.guard import Guard

    return Guard(backend=backend, config=cfg)


def _render_report(report, fmt: str) -> None:
    if fmt == "json":
        console.print_json(report.model_dump_json())
        return

    color = "green" if report.trust_score >= 0.8 else "yellow" if report.trust_score >= 0.6 else "red"
    console.print(
        Panel(
            f"[bold]Trust score[/bold]: [{color}]{report.trust_score:.2%}[/{color}]\n"
            f"[bold]SQL[/bold]: {report.sql or '—'}\n"
            f"[bold]Flags[/bold]: {', '.join(report.flags) or 'none'}",
            title="sql-guard report",
        )
    )
    table = Table("Check", "Score", "Passed", "Detail", title="Check breakdown")
    for cr in report.check_results:
        table.add_row(
            cr.check_name,
            f"{cr.score:.2f}",
            "✓" if cr.passed else "✗",
            cr.detail[:80],
        )
    console.print(table)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Natural language question"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    output: str = typer.Option("rich", "--output", "-o", help="rich | json"),
) -> None:
    """Ask a question through the configured backend and display the trust report."""
    guard = _load_guard(config)
    try:
        report = guard.ask(question)
        _render_report(report, output)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def verify(
    sql: str = typer.Option(..., "--sql", help="SQL to verify"),
    question: str = typer.Option(..., "--question", "-q", help="Original question"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    output: str = typer.Option("rich", "--output", "-o", help="rich | json"),
) -> None:
    """Run trust checks against an existing SQL query without calling a backend."""
    guard = _load_guard(config)
    report = guard.verify(question, sql)
    _render_report(report, output)


@app.command()
def dashboard(
    port: int = typer.Option(8501, "--port", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Launch the Streamlit dashboard."""
    import sql_guard.dashboard.app as _app_mod

    app_path = Path(_app_mod.__file__)
    cmd = ["streamlit", "run", str(app_path), "--server.port", str(port)]
    if config:
        cmd += ["--", "--config", str(config)]
    subprocess.run(cmd)


@app.command()
def report(
    since: str = typer.Option("7d", "--since"),
    fmt: str = typer.Option("rich", "--format", help="rich | json"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Generate a summary trust report for a time window."""
    from sql_guard.config import load_config
    from sql_guard.store.duckdb_store import DuckDBStore

    cfg = load_config(config)
    store = DuckDBStore(cfg.event_store, read_only=True)
    events = store.query_events(since=since, limit=1000)
    perf = store.get_latency_percentiles(since=since)

    if fmt == "json":
        console.print_json(json.dumps({"events": len(events), "perf": perf}))
        return

    console.print(f"\n[bold]Events in last {since}:[/bold] {len(events)}")
    if events:
        avg_trust = sum(e["trust_score"] or 0 for e in events) / len(events)
        console.print(f"[bold]Avg trust score:[/bold] {avg_trust:.2%}")
    console.print(f"[bold]Latency P50:[/bold] {perf['p50']} ms  P95: {perf['p95']} ms")


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p"),
    host: str = typer.Option("0.0.0.0", "--host"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev mode)"),
) -> None:
    """Start the sql-guard API server (proxy + push API endpoints)."""
    import uvicorn
    import sql_guard.server.main as server_mod

    if config:
        server_mod._config_path = config
    uvicorn.run(
        "sql_guard.server.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def ci(
    minimum: float = typer.Option(0.75, "--minimum", "-m"),
    since: str = typer.Option("24h", "--since"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """CI gate: exits 1 if average trust score is below minimum threshold."""
    from sql_guard.config import load_config
    from sql_guard.store.duckdb_store import DuckDBStore

    cfg = load_config(config)
    store = DuckDBStore(cfg.event_store, read_only=True)
    events = store.query_events(since=since, limit=10000)

    if not events:
        console.print(f"[yellow]No events in last {since}. Passing.[/yellow]")
        raise typer.Exit(0)

    avg = sum(e["trust_score"] or 0 for e in events) / len(events)
    if avg < minimum:
        console.print(
            f"[red]FAIL[/red] avg trust {avg:.2%} < minimum {minimum:.2%} "
            f"({len(events)} events in last {since})"
        )
        sys.exit(1)
    console.print(
        f"[green]PASS[/green] avg trust {avg:.2%} >= {minimum:.2%} "
        f"({len(events)} events in last {since})"
    )
