"""Synchronous HTTP health check."""
import time
import httpx
from .models import CheckResult


def check(url: str, timeout: float = 5.0) -> CheckResult:
    """Hit one URL and report the outcome."""
    start = time.perf_counter()
    try:
        response = httpx.get(url, timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            url=url,
            status=response.status_code,
            ok=200 <= response.status_code < 400,
            latency_ms=latency_ms,
        )
    except httpx.RequestError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            url=url,
            ok=False,
            latency_ms=latency_ms,
            error=str(exc),
        )