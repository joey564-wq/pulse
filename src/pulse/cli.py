"""Pulse CLI."""
import asyncio
from pathlib import Path

import typer

from .checker import check_many
from .config import load_services
from .db import CheckRecord, init_db, make_engine, record_to_row, session_scope
from .logging import configure_logging
from .models import CheckResult

app = typer.Typer(help="Pulse — service health monitor.")

# Module-level option definitions (avoids ruff B008: function calls in defaults).
CONFIG_OPTION = typer.Option(Path("services.toml"), "--config", "-c")
DB_OPTION = typer.Option(Path("pulse.db"), "--db")
URL_FILTER_OPTION = typer.Option(None, "--url", help="Filter by URL.")
LIMIT_OPTION = typer.Option(20, "--limit", "-n")
INTERVAL_OPTION = typer.Option(30.0, "--interval", "-i", help="Seconds between rounds.")


@app.callback()
def main() -> None:
    """Force typer into multi-command mode (so `pulse run` works)."""
    configure_logging()


@app.command("run")
def run_cmd(
    config: Path = CONFIG_OPTION,
    db: Path = DB_OPTION,
) -> None:
    """Run one round of checks across all configured services."""
    services = load_services(config)
    urls = [s.url for s in services]

    results = asyncio.run(check_many(urls))

    engine = make_engine(db)
    init_db(engine)
    with session_scope(engine) as session:
        for result in results:
            typer.echo(
                f"{result.url}  ok={result.ok}  status={result.status}  "
                f"latency_ms={result.latency_ms:.1f}"
            )
            session.add(record_to_row(result))


@app.command("history")
def history_cmd(
    url: str | None = URL_FILTER_OPTION,
    limit: int = LIMIT_OPTION,
    db: Path = DB_OPTION,
) -> None:
    """Print the most recent check records."""
    engine = make_engine(db)
    init_db(engine)

    with session_scope(engine) as session:
        query = session.query(CheckRecord).order_by(CheckRecord.checked_at.desc())
        if url is not None:
            query = query.filter(CheckRecord.url == url)
        rows = query.limit(limit).all()

    if not rows:
        typer.echo("No records yet.")
        return

    for row in rows:
        typer.echo(
            f"{row.checked_at.isoformat()}  {row.url}  "
            f"ok={row.ok}  status={row.status}  latency_ms={row.latency_ms:.1f}"
        )


@app.command("monitor")
def monitor_cmd(
    config: Path = CONFIG_OPTION,
    db: Path = DB_OPTION,
    interval: float = INTERVAL_OPTION,
) -> None:
    """Run checks repeatedly on a schedule. Press Ctrl-C to stop."""
    from .monitor import run_monitor

    services = load_services(config)
    urls = [s.url for s in services]
    engine = make_engine(db)

    def print_round(results: list[CheckResult]) -> None:
        for r in results:
            typer.echo(
                f"{r.checked_at.isoformat()}  {r.url}  ok={r.ok}  "
                f"status={r.status}  latency_ms={r.latency_ms:.1f}"
            )
        typer.echo("---")

    try:
        asyncio.run(run_monitor(urls, engine, interval_seconds=interval, on_round=print_round))
    except KeyboardInterrupt:
        typer.echo("\nStopped.")