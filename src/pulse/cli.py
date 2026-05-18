"""Command-line interface for pulse."""

from pathlib import Path

import typer

from pulse.checker import check
from pulse.config import load_services

app = typer.Typer(help="Pulse — a tiny service health monitor.", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Pulse — a tiny service health monitor."""


@app.command()
def run(
    config: Path = Path("services.toml"),
    timeout: float = 10.0,
) -> None:
    """Check every service listed in the config file."""
    services = load_services(config)
    if not services:
        typer.echo(f"No services found in {config}", err=True)
        raise typer.Exit(code=1)

    for service in services:
        result = check(service["url"], timeout=timeout)
        status_emoji = "✅" if result["ok"] else "❌"
        status_str = result["status"] if result["status"] is not None else "ERR"
        typer.echo(
            f"{status_emoji} {service['name']:12} {result['url']:40} "
            f"→ {status_str} ({result['latency_ms']}ms)"
        )


if __name__ == "__main__":
    app()
