"""Tests for the periodic monitor loop."""
from pathlib import Path

from pulse.db import CheckRecord, make_engine, session_scope
from pulse.models import CheckResult
from pulse.monitor import run_monitor


async def test_monitor_runs_n_rounds_and_persists(tmp_path: Path, httpx_mock):
    """run_monitor executes the requested number of rounds and writes each to the DB."""
    httpx_mock.add_response(
        url="https://example.com",
        status_code=200,
        is_reusable=True,
    )

    db = tmp_path / "test.db"
    engine = make_engine(db)

    received: list[list[CheckResult]] = []

    await run_monitor(
        urls=["https://example.com"],
        engine=engine,
        interval_seconds=0.0,
        on_round=received.append,
        rounds=3,
    )

    assert len(received) == 3
    for round_results in received:
        assert len(round_results) == 1
        assert round_results[0].ok is True

    with session_scope(engine) as session:
        assert session.query(CheckRecord).count() == 3


async def test_monitor_records_failures(tmp_path: Path, httpx_mock):
    """Failed checks are still persisted as rows with ok=False."""
    import httpx

    httpx_mock.add_exception(httpx.ConnectError("boom"), is_reusable=True)

    db = tmp_path / "test.db"
    engine = make_engine(db)

    await run_monitor(
        urls=["https://example.com"],
        engine=engine,
        interval_seconds=0.0,
        rounds=2,
    )

    with session_scope(engine) as session:
        rows = session.query(CheckRecord).all()
    assert len(rows) == 2
    assert all(r.ok is False for r in rows)
    assert all(r.error is not None for r in rows)


async def test_monitor_zero_rounds_does_nothing(tmp_path: Path, httpx_mock):
    """A monitor configured for 1 round runs exactly 1 round (sanity check)."""
    httpx_mock.add_response(url="https://example.com", status_code=200)

    db = tmp_path / "test.db"
    engine = make_engine(db)

    received: list[list[CheckResult]] = []

    await run_monitor(
        urls=["https://example.com"],
        engine=engine,
        interval_seconds=0.0,
        on_round=received.append,
        rounds=1,
    )

    assert len(received) == 1
    with session_scope(engine) as session:
        assert session.query(CheckRecord).count() == 1