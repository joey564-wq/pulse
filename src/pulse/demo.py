"""Synthetic data + one-shot server start for demos.

Service URLs are prefixed `demo-` so anyone looking at the dashboard
understands this is seeded data, not real monitoring. RNG seed is fixed
so the same `pulse demo` produces the same dashboard every time.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.engine import Engine

from .db import AlertEventRow, AlertStateRow, CheckRecord, session_scope

DEMO_SERVICES: list[tuple[str, float, float]] = [
    # (url, baseline_latency_ms, failure_rate)
    ("https://demo-fast-api.example", 45.0, 0.001),
    ("https://demo-slow-api.example", 320.0, 0.010),
    ("https://demo-flaky-cdn.example", 90.0, 0.050),
    ("https://demo-outage-prone.example", 180.0, 0.150),
]


def seed(engine: Engine, hours: int = 24) -> int:
    """Seed `hours` of synthetic checks at 1-minute intervals.

    Returns the number of check records written (alert rows are not counted).
    """
    rng = random.Random(42)  # reproducible — same demo every run
    now = datetime.now(UTC)

    rows: list[CheckRecord] = []
    for url, base_lat, fail_rate in DEMO_SERVICES:
        for minutes_ago in range(hours * 60):
            ts = now - timedelta(minutes=minutes_ago)
            failed = rng.random() < fail_rate
            latency = max(5.0, rng.gauss(base_lat, base_lat * 0.2))
            rows.append(
                CheckRecord(
                    url=url,
                    status=503 if failed else 200,
                    ok=not failed,
                    latency_ms=latency,
                    error="HTTP 503" if failed else None,
                    checked_at=ts,
                )
            )

    with session_scope(engine) as session:
        session.add_all(rows)

    # One currently-active alert + one historical fired/recovered pair —
    # gives the dashboard's "Recent alerts" panel something to show.
    with session_scope(engine) as session:
        session.add(
            AlertStateRow(
                url="https://demo-outage-prone.example",
                consecutive_failures=4,
                active=True,
                last_event_at=now - timedelta(minutes=12),
            )
        )
        session.add(
            AlertEventRow(
                url="https://demo-outage-prone.example",
                kind="failing",
                occurred_at=now - timedelta(minutes=12),
                consecutive_failures=3,
            )
        )
        session.add(
            AlertEventRow(
                url="https://demo-flaky-cdn.example",
                kind="recovered",
                occurred_at=now - timedelta(hours=3),
                consecutive_failures=0,
            )
        )

    return len(rows)
