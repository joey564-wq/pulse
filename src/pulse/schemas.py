"""Pydantic response models for the API."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, field_serializer


def _ensure_utc_iso(dt: datetime | None) -> str | None:
    """Serialize a datetime as ISO 8601 with an explicit UTC suffix.

    SQLAlchemy returns naive datetimes from SQLite even though we wrote
    UTC-aware values. Without an explicit suffix, JS `new Date(...)` parses
    the string as local time, which breaks "N seconds ago" math.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


class CheckRecordOut(BaseModel):
    url: str
    ok: bool
    status: int | None
    latency_ms: float
    error: str | None
    checked_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("checked_at")
    def _ser_checked_at(self, dt: datetime) -> str:
        return _ensure_utc_iso(dt) or ""


class ServiceSummaryOut(BaseModel):
    url: str
    total_checks: int
    successful_checks: int
    uptime_pct: float
    avg_latency_ms: float | None
    last_checked_at: datetime | None

    model_config = {"from_attributes": True}

    @field_serializer("last_checked_at")
    def _ser_last_checked_at(self, dt: datetime | None) -> str | None:
        return _ensure_utc_iso(dt)


class OverallStatsOut(BaseModel):
    services_tracked: int
    total_checks: int
    successful_checks: int
    overall_uptime_pct: float
    first_checked_at: datetime | None
    last_checked_at: datetime | None
    alerts_fired: int
    alerts_recovered: int
    active_alerts: int

    model_config = {"from_attributes": True}

    @field_serializer("first_checked_at", "last_checked_at")
    def _ser_dt(self, dt: datetime | None) -> str | None:
        return _ensure_utc_iso(dt)


class AlertEventOut(BaseModel):
    url: str
    kind: str
    occurred_at: datetime
    consecutive_failures: int

    model_config = {"from_attributes": True}

    @field_serializer("occurred_at")
    def _ser_occurred_at(self, dt: datetime) -> str:
        return _ensure_utc_iso(dt) or ""
