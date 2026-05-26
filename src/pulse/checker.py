"""Async HTTP health checks."""

import asyncio
import time
from collections.abc import Iterable

import httpx

from .models import CheckResult


async def check_one(
    url: str,
    client: httpx.AsyncClient,
    timeout: float = 5.0,
) -> CheckResult:
    """Hit one URL using a shared AsyncClient and report the outcome."""
    start = time.perf_counter()
    try:
        response = await client.get(url, timeout=timeout)
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


async def check_many(urls: Iterable[str], timeout: float = 5.0) -> list[CheckResult]:
    """Run check_one concurrently across many URLs and return all results."""
    async with httpx.AsyncClient() as client:
        coroutines = [check_one(url, client, timeout) for url in urls]
        return await asyncio.gather(*coroutines)
