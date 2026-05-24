"""Read queries used by the CLI and the API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pulse.db import CheckRecord


@dataclass(frozen=True, slots=True)
class ServiceSummary:
    url: str
    total_checks: int
    successful_checks: int
    uptime_pct: float
    avg_latency_ms: float | None
    last_checked_at: datetime | None


def list_service_urls(session: Session) -> list[str]:
    """All distinct service URLs we have records for."""
    stmt = select(CheckRecord.url).distinct().order_by(CheckRecord.url)
    return list(session.execute(stmt).scalars())


def get_history(
    session: Session,
    url: str | None = None,
    limit: int = 100,
) -> list[CheckRecord]:
    """Most recent check records, newest first. If url is None, returns all."""
    stmt = select(CheckRecord).order_by(CheckRecord.checked_at.desc())
    if url is not None:
        stmt = stmt.where(CheckRecord.url == url)
    stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars())


def get_summary(session: Session, url: str) -> ServiceSummary:
    """Aggregate stats for one service."""
    total = session.scalar(
        select(func.count()).select_from(CheckRecord).where(CheckRecord.url == url)
    ) or 0

    successful = session.scalar(
        select(func.count())
        .select_from(CheckRecord)
        .where(CheckRecord.url == url, CheckRecord.ok.is_(True))
    ) or 0

    avg_latency = session.scalar(
        select(func.avg(CheckRecord.latency_ms))
        .where(CheckRecord.url == url, CheckRecord.ok.is_(True))
    )

    last_checked = session.scalar(
        select(func.max(CheckRecord.checked_at)).where(CheckRecord.url == url)
    )

    return ServiceSummary(
        url=url,
        total_checks=total,
        successful_checks=successful,
        uptime_pct=(successful / total * 100.0) if total else 0.0,
        avg_latency_ms=float(avg_latency) if avg_latency is not None else None,
        last_checked_at=last_checked,
    )


def get_all_summaries(session: Session) -> list[ServiceSummary]:
    """Aggregate stats for every known service."""
    return [get_summary(session, url) for url in list_service_urls(session)]