import time

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


def main(url: str, timeout: float = 10.0, verbose: bool = False) -> None:
    """Ping a URL and report status and latency."""
    result = check(url, timeout=timeout)
    if verbose:
        print(result)
    else:
        status_emoji = "✅" if result["ok"] else "❌"
        status_str = result["status"] if result["status"] is not None else "ERR"
        print(f"{status_emoji} {result['url']} → {status_str} ({result['latency_ms']}ms)")
        if result["error"]:
            print(f"   error: {result['error']}")


if __name__ == "__main__":
    typer.run(main)