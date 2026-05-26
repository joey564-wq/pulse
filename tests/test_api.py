"""Tests for the FastAPI app."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pulse.api import app, get_session
from pulse.db import CheckRecord, init_db, make_engine, session_scope


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient with a fresh per-test DB and three seed records."""
    db_path = tmp_path / "test.db"
    engine = make_engine(db_path)
    init_db(engine)

    with session_scope(engine) as session:
        session.add_all(
            [
                CheckRecord(
                    url="https://example.com",
                    ok=True,
                    status=200,
                    latency_ms=40.0,
                    error=None,
                    checked_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                ),
                CheckRecord(
                    url="https://example.com",
                    ok=True,
                    status=200,
                    latency_ms=60.0,
                    error=None,
                    checked_at=datetime(2026, 5, 1, 12, 1, tzinfo=UTC),
                ),
                CheckRecord(
                    url="https://example.com",
                    ok=False,
                    status=None,
                    latency_ms=5000.0,
                    error="timeout",
                    checked_at=datetime(2026, 5, 1, 12, 2, tzinfo=UTC),
                ),
            ]
        )

    def override_get_session() -> Iterator:
        with session_scope(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_services_lists_known_urls(client: TestClient) -> None:
    response = client.get("/services")
    assert response.status_code == 200
    assert response.json() == ["https://example.com"]


def test_history_returns_records_for_url(client: TestClient) -> None:
    response = client.get("/history", params={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Newest first
    assert data[0]["error"] == "timeout"
    assert data[0]["ok"] is False
    assert data[2]["latency_ms"] == 40.0


def test_history_empty_for_unknown_url(client: TestClient) -> None:
    response = client.get("/history", params={"url": "https://other.com"})
    assert response.status_code == 200
    assert response.json() == []


def test_summary_returns_one_per_service(client: TestClient) -> None:
    response = client.get("/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    s = data[0]
    assert s["url"] == "https://example.com"
    assert s["total_checks"] == 3
    assert s["successful_checks"] == 2
    assert s["uptime_pct"] == pytest.approx(66.666, rel=1e-3)
    # Only OK checks contribute: avg(40, 60) = 50.0
    assert s["avg_latency_ms"] == pytest.approx(50.0)


def test_summary_for_unknown_url_is_zeros(client: TestClient) -> None:
    response = client.get("/summary/https%3A%2F%2Fnope.com")
    assert response.status_code == 200
    data = response.json()
    assert data["total_checks"] == 0
    assert data["uptime_pct"] == 0.0
    assert data["avg_latency_ms"] is None


def test_root_serves_dashboard(client: TestClient) -> None:
    """The root path serves the dashboard HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Pulse</title>" in response.text


def test_static_mount_returns_404_for_missing_file(client: TestClient) -> None:
    """Tripwire: confirms the static mount works (404, not 500)."""
    response = client.get("/static/nonexistent.css")
    assert response.status_code == 404
