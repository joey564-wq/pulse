"""Pulse CLI."""
import asyncio
from pathlib import Path

import typer

from .checker import check_many
from .config import load_services
from .db import init_db, make_engine, record_to_row, session_scope
from .logging import configure_logging
from .queries import get_history

app = typer.Typer(help="Pulse — service health monitor.")

# Module-level option definitions (avoids ruff B008: function calls in defaults).
CONFIG_OPTION = typer.Option(Path("services.toml"), "--config", "-c")
DB_OPTION = typer.Option(Path("pulse.db"), "--db")
URL_FILTER_OPTION = typer.Option(None, "--url", help="Filter by URL.")
LIMIT_OPTION = typer.Option(20, "--limit", "-n")
ROUNDS_OPTION = typer.Option(
    None,
    "--rounds",
    "-r",
    help="Stop after N rounds per service. Default: run until Ctrl-C.",
)
ALERTS_FILE_OPTION = typer.Option(
    Path("alerts.log"),
    "--alerts-file",
    help="Path to append alert events as JSON lines.",
)


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
        rows = get_history(session, url=url, limit=limit)

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
    rounds: int | None = ROUNDS_OPTION,
    alerts_file: Path = ALERTS_FILE_OPTION,
) -> None:
    """Run checks repeatedly on per-service schedules. Press Ctrl-C to stop."""
    from .alerts import AlertTracker, CompositeNotifier, FileNotifier, LogNotifier
    from .models import CheckResult, Service
    from .monitor import run_monitor

    services = load_services(config)
    engine = make_engine(db)
    init_db(engine)

    tracker = AlertTracker()
    notifier = CompositeNotifier(LogNotifier(), FileNotifier(alerts_file))

    def on_result(service: Service, result: CheckResult) -> None:
        typer.echo(
            f"{result.checked_at.isoformat()}  {service.name or service.url}  "
            f"ok={result.ok}  status={result.status}  "
            f"latency_ms={result.latency_ms:.1f}"
        )
        event = tracker.record(service, result)
        if event is not None:
            notifier.notify(event)

    try:
        asyncio.run(run_monitor(services, engine, on_result=on_result, rounds=rounds))
    except KeyboardInterrupt:
        typer.echo("\nStopped.")