import time
import tomllib
from pathlib import Path

import httpx
import typer


def check(url: str, timeout: float = 10.0) -> dict:
    """Check a single URL. Return a dict describing the result."""
    start = time.perf_counter()
    try:
        response = httpx.get(url, timeout=timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "url": url,
            "status": response.status_code,
            "ok": response.status_code < 400,
            "latency_ms": round(elapsed_ms, 1),
            "error": None,
        }
    except httpx.RequestError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "url": url,
            "status": None,
            "ok": False,
            "latency_ms": round(elapsed_ms, 1),
            "error": str(exc),
        }


def load_services(path: Path) -> list[dict]:
    """Load the list of services from a TOML config file."""
    with path.open("rb") as f:
        config = tomllib.load(f)
    return config.get("services", [])


def main(config: Path = Path("services.toml"), timeout: float = 10.0) -> None:
    """Check every service listed in the config file."""
    services = load_services(config)
    if not services:
        print(f"No services found in {config}")
        raise typer.Exit(code=1)

    for service in services:
        result = check(service["url"], timeout=timeout)
        status_emoji = "✅" if result["ok"] else "❌"
        status_str = result["status"] if result["status"] is not None else "ERR"
        print(
            f"{status_emoji} {service['name']:12} {result['url']:40} "
            f"→ {status_str} ({result['latency_ms']}ms)"
        )


if __name__ == "__main__":
    typer.run(main)