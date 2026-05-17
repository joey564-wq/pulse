import time

import httpx


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


if __name__ == "__main__":
    for url in [
        "https://example.com",
        "https://example.com/definitely-not-a-real-page",
        "http://localhost:9999",  # nothing listening — should fail
    ]:
        print(check(url))