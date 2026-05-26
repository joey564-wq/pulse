"""Tests for the periodic monitor loop."""

from pathlib import Path

import httpx
from pytest_httpx import HTTPXMock
from sqlalchemy import select

from pulse.db import CheckRecord, init_db, make_engine, session_scope
from pulse.models import CheckResult, Service
from pulse.monitor import run_monitor


def make_service(url: str = "https://example.com", name: str = "example") -> Service:
    """Factory for test services with a fast interval."""
    return Service(
        url=url,
        name=name,
        interval_seconds=0.001,  # gt=0 validator rejects 0.0, so use 1ms
        timeout_seconds=5.0,
        alert_after_failures=3,
    )


async def test_monitor_runs_n_rounds_and_persists(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    """run_monitor executes the requested number of rounds per service and writes each to the DB."""
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        is_reusable=True,
    )

    db = tmp_path / "test.db"
    engine = make_engine(db)
    init_db(engine)

    received: list[tuple[Service, CheckResult]] = []

    def on_result(service: Service, result: CheckResult) -> None:
        received.append((service, result))

    await run_monitor(
        [make_service()],
        engine,
        on_result=on_result,
        rounds=3,
    )

    assert len(received) == 3
    for service, result in received:
        assert service.url == "https://example.com"
        assert result.ok is True

    with session_scope(engine) as session:
        assert session.query(CheckRecord).count() == 3


async def test_monitor_records_failures(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    """Failed checks are still persisted as rows with ok=False."""
    httpx_mock.add_exception(httpx.ConnectError("boom"), is_reusable=True)

    db = tmp_path / "test.db"
    engine = make_engine(db)
    init_db(engine)

    await run_monitor(
        [make_service()],
        engine,
        rounds=2,
    )

    with session_scope(engine) as session:
        rows = session.query(CheckRecord).all()
    assert len(rows) == 2
    assert all(r.ok is False for r in rows)
    assert all(r.error is not None for r in rows)


async def test_monitor_single_round(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    """A monitor configured for 1 round runs exactly 1 round (sanity check)."""
    httpx_mock.add_response(url="https://example.com", status_code=200)

    db = tmp_path / "test.db"
    engine = make_engine(db)
    init_db(engine)

    received: list[tuple[Service, CheckResult]] = []

    def on_result(service: Service, result: CheckResult) -> None:
        received.append((service, result))

    await run_monitor(
        [make_service()],
        engine,
        on_result=on_result,
        rounds=1,
    )

    assert len(received) == 1
    with session_scope(engine) as session:
        assert session.query(CheckRecord).count() == 1


async def test_monitor_runs_multiple_services_concurrently(
    tmp_path: Path, httpx_mock: HTTPXMock
) -> None:
    """Each service runs as its own task; all services tick independently."""
    httpx_mock.add_response(url="https://a.example.com", status_code=200, is_reusable=True)
    httpx_mock.add_response(url="https://b.example.com", status_code=200, is_reusable=True)

    db = tmp_path / "test.db"
    engine = make_engine(db)
    init_db(engine)

    services = [
        make_service("https://a.example.com", name="a"),
        make_service("https://b.example.com", name="b"),
    ]

    await run_monitor(services, engine, rounds=2)

    with session_scope(engine) as session:
        rows = session.query(CheckRecord).all()

    # 2 services × 2 rounds each = 4 rows total
    assert len(rows) == 4
    urls = {r.url for r in rows}
    assert urls == {"https://a.example.com", "https://b.example.com"}


async def test_one_failing_service_does_not_kill_others(engine, monkeypatch):
    """A service that raises in check_one must not stop other services."""
    from datetime import UTC, datetime

    from pulse import monitor as monitor_mod

    async def flaky_check_one(url, _client, _timeout):
        if "broken" in url:
            raise RuntimeError("simulated network meltdown")
        return CheckResult(
            url=url,
            status=200,
            ok=True,
            latency_ms=10.0,
            error=None,
            checked_at=datetime.now(UTC),
        )

    monkeypatch.setattr(monitor_mod, "check_one", flaky_check_one)

    services = [
        Service(url="https://example.com", interval_seconds=1),
        Service(url="http://broken.invalid", interval_seconds=1),
    ]
    await run_monitor(services, engine, rounds=2)

    with session_scope(engine) as session:
        rows = session.scalars(
            select(CheckRecord).where(CheckRecord.url == "https://example.com")
        ).all()
    assert len(rows) == 2  # healthy service ran both rounds
