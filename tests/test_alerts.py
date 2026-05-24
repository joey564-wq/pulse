"""Tests for alert tracking and notifiers."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pulse.alerts import AlertTracker, FileNotifier
from pulse.models import CheckResult, Service


def make_service(threshold: int = 2) -> Service:
    return Service(
        url="https://example.com",
        name="example",
        interval_seconds=1.0,
        timeout_seconds=5.0,
        alert_after_failures=threshold,
    )


def make_result(ok: bool) -> CheckResult:
    return CheckResult(
        url="https://example.com",
        ok=ok,
        status=200 if ok else None,
        latency_ms=10.0,
        error=None if ok else "fail",
        checked_at=datetime(2026, 5, 1, tzinfo=UTC),
    )


def test_no_alert_below_threshold() -> None:
    tracker = AlertTracker()
    service = make_service(threshold=3)
    assert tracker.record(service, make_result(ok=False)) is None
    assert tracker.record(service, make_result(ok=False)) is None


def test_alert_fires_at_threshold() -> None:
    tracker = AlertTracker()
    service = make_service(threshold=2)
    assert tracker.record(service, make_result(ok=False)) is None
    event = tracker.record(service, make_result(ok=False))
    assert event is not None
    assert event.kind == "failing"
    assert event.consecutive_failures == 2


def test_alert_does_not_refire_while_active() -> None:
    tracker = AlertTracker()
    service = make_service(threshold=2)
    tracker.record(service, make_result(ok=False))
    tracker.record(service, make_result(ok=False))   # fires "failing"
    event = tracker.record(service, make_result(ok=False))
    assert event is None  # already alerting, don't re-fire


def test_recovery_event_after_alert() -> None:
    tracker = AlertTracker()
    service = make_service(threshold=2)
    tracker.record(service, make_result(ok=False))
    tracker.record(service, make_result(ok=False))   # fires "failing"
    event = tracker.record(service, make_result(ok=True))
    assert event is not None
    assert event.kind == "recovered"


def test_success_before_threshold_resets_counter() -> None:
    tracker = AlertTracker()
    service = make_service(threshold=3)
    tracker.record(service, make_result(ok=False))
    tracker.record(service, make_result(ok=False))
    tracker.record(service, make_result(ok=True))   # resets
    event = tracker.record(service, make_result(ok=False))
    assert event is None  # only one consecutive failure now


def test_file_notifier_writes_jsonl(tmp_path: Path) -> None:
    import json
    notifier = FileNotifier(tmp_path / "alerts.log")
    tracker = AlertTracker()
    service = make_service(threshold=1)
    event = tracker.record(service, make_result(ok=False))
    assert event is not None
    notifier.notify(event)

    lines = (tmp_path / "alerts.log").read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["url"] == "https://example.com"
    assert data["kind"] == "failing"