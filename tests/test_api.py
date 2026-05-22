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
    """A TestClient with a fresh per-test DB and one seed record."""
    db_path = tmp_path / "test.db"
    engine = make_engine(db_path)
    init_db(engine)

    with session_scope(engine) as session:
        session.add(
            CheckRecord(
                url="https://example.com",
                ok=True,
                status=200,
                latency_ms=42.0,
                error=None,
                checked_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            )
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
    assert len(data) == 1
    assert data[0]["url"] == "https://example.com"
    assert data[0]["ok"] is True
    assert data[0]["latency_ms"] == 42.0


def test_history_empty_for_unknown_url(client: TestClient) -> None:
    response = client.get("/history", params={"url": "https://other.com"})
    assert response.status_code == 200
    assert response.json() == []