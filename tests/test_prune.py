# tests/test_prune.py
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pulse.config import ConfigError, load_services
from pulse.db import CheckRecord, session_scope
from pulse.queries import prune_keep_last_per_service, prune_older_than


def _seed(engine, url: str, ages_days: list[float]) -> None:
    now = datetime.now(UTC)
    with session_scope(engine) as session:
        for age in ages_days:
            session.add(
                CheckRecord(
                    url=url,
                    status=200,
                    ok=True,
                    latency_ms=10.0,
                    error=None,
                    checked_at=now - timedelta(days=age),
                )
            )


def test_prune_older_than(engine):
    _seed(engine, "https://a", [0.1, 5.0, 31.0, 60.0])
    deleted = prune_older_than(engine, days=30)
    assert deleted == 2
    with session_scope(engine) as session:
        remaining = session.scalars(select(CheckRecord)).all()
    assert len(remaining) == 2


def test_prune_keep_last_per_service(engine):
    _seed(engine, "https://a", [0.1, 0.2, 0.3, 0.4, 0.5])
    _seed(engine, "https://b", [0.1, 0.2])
    deleted = prune_keep_last_per_service(engine, keep=2)
    assert deleted == 3  # 5-2 from a, 0 from b


def test_load_services_friendly_error_on_bad_value(tmp_path):
    bad = tmp_path / "services.toml"
    bad.write_text('[[services]]\nurl = "https://example.com"\ninterval_seconds = 0\n')
    with pytest.raises(ConfigError) as exc_info:
        load_services(bad)
    assert "interval_seconds" in str(exc_info.value)


def test_load_services_friendly_error_on_bad_toml(tmp_path):
    bad = tmp_path / "services.toml"
    bad.write_text("[[services\n url = 'oops'")
    with pytest.raises(ConfigError) as exc_info:
        load_services(bad)
    assert "parse" in str(exc_info.value).lower()
