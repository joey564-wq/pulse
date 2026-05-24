"""Periodic monitoring loop with per-service intervals."""
from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx
from sqlalchemy import Engine

from .checker import check_one
from .db import record_to_row, session_scope
from .logging import get_logger
from .models import CheckResult, Service

log = get_logger(__name__)

OnResult = Callable[[Service, CheckResult], None]


async def _run_one_service(
    service: Service,
    client: httpx.AsyncClient,
    engine: Engine,
    on_result: OnResult | None = None,
    rounds: int | None = None,
) -> None:
    """Periodically check a single service forever (or for `rounds` iterations)."""
    count = 0
    while rounds is None or count < rounds:
        result = await check_one(service.url, client, timeout=service.timeout_seconds)
        with session_scope(engine) as session:
            session.add(record_to_row(result))
        log.info(
            "checked",
            url=service.url,
            ok=result.ok,
            latency_ms=result.latency_ms,
        )
        if on_result is not None:
            on_result(service, result)
        count += 1
        # Skip the final sleep so the function returns promptly on the last round.
        if rounds is None or count < rounds:
            await asyncio.sleep(service.interval_seconds)


async def run_monitor(
    services: list[Service],
    engine: Engine,
    *,
    on_result: OnResult | None = None,
    rounds: int | None = None,
) -> None:
    """Run checks for all services concurrently with per-service intervals.

    Each service runs as its own task on the event loop with its own
    interval and timeout. All tasks share one httpx.AsyncClient for
    connection pooling.
    """
    async with httpx.AsyncClient() as client:
        tasks = [
            _run_one_service(s, client, engine, on_result=on_result, rounds=rounds)
            for s in services
        ]
        await asyncio.gather(*tasks)