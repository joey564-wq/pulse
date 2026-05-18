"""Pydantic data models for Pulse."""
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """UTC-aware 'now'. Avoids the deprecated naive datetime.utcnow()."""
    return datetime.now(timezone.utc)


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
    name: str | None = None