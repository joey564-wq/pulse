"""Per-service monitor loop. One task per service, isolated and gracefully cancellable."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Iterable

import httpx
import structlog
from sqlalchemy.engine import Engine

from .checker import check_one
from .db import CheckRecord, session_scope
from .models import CheckResult, Service

log = structlog.get_logger()

OnResult = Callable[[Service, CheckResult], Awaitable[None] | None]


async def _run_one_service(
    service: Service,
    client: httpx.AsyncClient,
    engine: Engine,
    on_result: OnResult | None,
    rounds: int | None,
    stop: asyncio.Event,
) -> None:
    """Check loop for one service. Failures stay local; never raises."""
    iteration = 0
    while True:
        if stop.is_set():
            return
        if rounds is not None and iteration >= rounds:
            return

        try:
            result = await check_one(service.url, client, service.timeout_seconds)
            with session_scope(engine) as session:
                session.add(
                    CheckRecord(
                        url=service.url,
                        status=result.status,  # NOT status_code
                        ok=result.ok,
                        latency_ms=result.latency_ms,
                        error=result.error,
                        checked_at=result.checked_at,
                    )
                )
            if on_result is not None:
                maybe = on_result(service, result)
                if asyncio.iscoroutine(maybe):
                    await maybe
        except Exception:
            # Per-service isolation: log and continue looping.
            log.exception("service_task_error", url=service.url)

        iteration += 1
        if rounds is not None and iteration >= rounds:
            return

        # Sleep, but wake early on shutdown.
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=service.interval_seconds)
            return  # only get here if stop was set during sleep


async def run_monitor(
    services: Iterable[Service],
    engine: Engine,
    *,
    on_result: OnResult | None = None,
    rounds: int | None = None,
    stop: asyncio.Event | None = None,
) -> None:
    """Run all services concurrently. Returns when all tasks finish or `stop` is set."""
    stop = stop or asyncio.Event()
    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(
                _run_one_service(s, client, engine, on_result, rounds, stop),
                name=f"pulse:{s.name or s.url}",
            )
            for s in services
        ]
        # return_exceptions=True: if anything escapes _run_one_service's own
        # try/except (it shouldn't), don't take the other tasks down with it.
        await asyncio.gather(*tasks, return_exceptions=True)
