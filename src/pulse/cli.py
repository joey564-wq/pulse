"""Pulse CLI."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from .checker import check_many
from .config import ConfigError, load_services
from .db import init_db, make_engine, record_to_row, session_scope
from .logging import configure_logging
from .queries import get_history

if TYPE_CHECKING:
    from .models import Service

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

HOST_OPT = typer.Option("127.0.0.1", "--host", help="Host for the web server.")
PORT_OPT = typer.Option(8000, "--port", "-p", help="Port for the web server.")
RELOAD_OPT = typer.Option(False, "--reload", help="Enable auto-reload during development.")

# Week 4 additions.
DAYS_OPTION = typer.Option(None, "--days", help="Delete records older than N days.")
KEEP_LAST_OPTION = typer.Option(
    None,
    "--keep-last",
    help="Keep only the most recent N records per service.",
)
DEMO_DB_OPTION = typer.Option(
    Path("pulse-demo.db"),
    "--db",
    help="Demo database path (recreated each run).",
)
HOURS_OPTION = typer.Option(24, "--hours", help="Hours of synthetic history to seed.")
NO_SERVE_OPTION = typer.Option(
    False,
    "--no-serve",
    help="Just seed the demo DB; do not start the server.",
)


@app.callback()
def main() -> None:
    """Force typer into multi-command mode (so `pulse run` works)."""
    configure_logging()


def _load_or_die(config: Path) -> list["Service"]:
    """Load services with a friendly one-line error on bad config."""
    try:
        return load_services(config)
    except ConfigError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=2) from e


@app.command("run")
def run_cmd(
    config: Path = CONFIG_OPTION,
    db: Path = DB_OPTION,
) -> None:
    """Run one round of checks across all configured services."""
    services = _load_or_die(config)
    urls = [s.url for s in services]

    results = asyncio.run(check_many(urls))

    engine = make_engine(db)
    init_db(engine)
    try:
        with session_scope(engine) as session:
            for result in results:
                typer.echo(
                    f"{result.url}  ok={result.ok}  status={result.status}  "
                    f"latency_ms={result.latency_ms:.1f}"
                )
                session.add(record_to_row(result))
    finally:
        engine.dispose()


@app.command("history")
def history_cmd(
    url: str | None = URL_FILTER_OPTION,
    limit: int = LIMIT_OPTION,
    db: Path = DB_OPTION,
) -> None:
    """Print the most recent check records."""
    engine = make_engine(db)
    init_db(engine)
    try:
        with session_scope(engine) as session:
            rows = get_history(session, url=url, limit=limit)
    finally:
        engine.dispose()

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
    from .alerts_persistence import load_tracker, persist_observation
    from .models import CheckResult, Service
    from .monitor import run_monitor

    services = _load_or_die(config)
    engine = make_engine(db)
    init_db(engine)

    tracker = AlertTracker()
    load_tracker(engine, tracker)
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
        state = tracker.state_for(service.url)
        persist_observation(
            engine,
            url=service.url,
            consecutive_failures=state.consecutive_failures,
            active=state.active,
            event=event,
        )

    try:
        asyncio.run(run_monitor(services, engine, on_result=on_result, rounds=rounds))
    except KeyboardInterrupt:
        typer.echo("\nStopped.")
    finally:
        engine.dispose()


@app.command()
def serve(
    host: str = HOST_OPT,
    port: int = PORT_OPT,
    reload: bool = RELOAD_OPT,
    db: Path = DB_OPTION,
) -> None:
    """Run the Pulse web server (API + dashboard)."""
    import uvicorn

    os.environ["PULSE_DB"] = str(db)
    uvicorn.run("pulse.api:app", host=host, port=port, reload=reload)


@app.command()
def prune(
    db: Path = DB_OPTION,
    days: int | None = DAYS_OPTION,
    keep_last: int | None = KEEP_LAST_OPTION,
) -> None:
    """Delete old check records. Specify exactly one of --days or --keep-last."""
    from .queries import prune_keep_last_per_service, prune_older_than

    if (days is None) == (keep_last is None):
        typer.echo("error: specify exactly one of --days or --keep-last", err=True)
        raise typer.Exit(code=2)

    engine = make_engine(db)
    init_db(engine)
    try:
        if days is not None:
            n = prune_older_than(engine, days=days)
        else:
            assert keep_last is not None  # narrowed by the XOR check above
            n = prune_keep_last_per_service(engine, keep=keep_last)
    finally:
        engine.dispose()
    typer.echo(f"Deleted {n} record(s).")


@app.command()
def stats(
    db: Path = DB_OPTION,
) -> None:
    """One-page snapshot of monitoring history."""
    from .queries import get_overall_stats

    engine = make_engine(db)
    init_db(engine)
    try:
        with session_scope(engine) as session:
            s = get_overall_stats(session)
    finally:
        engine.dispose()

    def fmt_dt(dt: datetime | None) -> str:
        return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "—"

    if s.first_checked_at and s.last_checked_at:
        duration = str(s.last_checked_at - s.first_checked_at).split(".")[0]
    else:
        duration = "—"

    lines = [
        "Pulse — overall",
        "",
        f"  services tracked     {s.services_tracked}",
        f"  total checks         {s.total_checks:,}",
        f"  successful           {s.successful_checks:,}  ({s.overall_uptime_pct:.2f}%)",
        f"  first record         {fmt_dt(s.first_checked_at)}",
        f"  last record          {fmt_dt(s.last_checked_at)}",
        f"  duration             {duration}",
        "",
        f"  alerts fired         {s.alerts_fired}",
        f"  alerts recovered     {s.alerts_recovered}",
        f"  currently active     {s.active_alerts}",
    ]
    typer.echo("\n".join(lines))


@app.command()
def demo(
    db: Path = DEMO_DB_OPTION,
    hours: int = HOURS_OPTION,
    host: str = HOST_OPT,
    port: int = PORT_OPT,
    no_serve: bool = NO_SERVE_OPTION,
) -> None:
    """Seed a demo DB with synthetic data and start the dashboard."""
    from .demo import seed

    if db.exists():
        db.unlink()
    engine = make_engine(db)
    init_db(engine)
    try:
        n = seed(engine, hours=hours)
    finally:
        engine.dispose()
    typer.echo(f"Seeded {n:,} synthetic checks into {db}.")

    if no_serve:
        return

    import uvicorn

    os.environ["PULSE_DB"] = str(db)
    typer.echo(f"Starting dashboard at http://{host}:{port}  (Ctrl-C to stop)")
    uvicorn.run("pulse.api:app", host=host, port=port, log_level="warning")
