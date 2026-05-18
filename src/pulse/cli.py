"""Pulse CLI."""
from pathlib import Path

import typer

from .checker import check
from .config import load_services
from .db import CheckRecord, init_db, make_engine, record_to_row, session_scope

app = typer.Typer(help="Pulse — service health monitor.")


@app.callback()
def main() -> None:
    """Force typer into multi-command mode (so `pulse run` works)."""


@app.command("run")
def run_cmd(
    config: Path = typer.Option(Path("services.toml"), "--config", "-c"),
    db: Path = typer.Option(Path("pulse.db"), "--db"),
) -> None:
    """Run one round of checks across all configured services."""
    services = load_services(config)
    engine = make_engine(db)
    init_db(engine)

    with session_scope(engine) as session:
        for svc in services:
            result = check(svc.url)
            typer.echo(
                f"{result.url}  ok={result.ok}  status={result.status}  "
                f"latency_ms={result.latency_ms:.1f}"
            )
            session.add(record_to_row(result))


@app.command("history")
def history_cmd(
    url: str | None = typer.Option(None, "--url", help="Filter by URL."),
    limit: int = typer.Option(20, "--limit", "-n"),
    db: Path = typer.Option(Path("pulse.db"), "--db"),
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