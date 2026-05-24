"""Pydantic response models for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheckRecordOut(BaseModel):
    url: str
    ok: bool
    status: int | None
    latency_ms: float
    error: str | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class ServiceSummaryOut(BaseModel):
    url: str
    total_checks: int
    successful_checks: int
    uptime_pct: float
    avg_latency_ms: float | None
    last_checked_at: datetime | None

    model_config = {"from_attributes": True}