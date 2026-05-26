"""Pydantic data models for Pulse."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """UTC-aware 'now'. Avoids the deprecated naive datetime.utcnow()."""
    return datetime.now(UTC)


class CheckResult(BaseModel):
    """The outcome of a single health check against one URL."""

    url: str
    status: int | None = None
    ok: bool
    latency_ms: float
    error: str | None = None
    checked_at: datetime = Field(default_factory=_utcnow)


class Service(BaseModel):
    """A service to monitor, as declared in services.toml."""

    url: str
    name: str = Field(default="", description="Display name; defaults to URL hostname")
    interval_seconds: float = Field(default=60.0, gt=0)
    timeout_seconds: float = Field(default=5.0, gt=0)
    alert_after_failures: int = Field(default=3, ge=1)
