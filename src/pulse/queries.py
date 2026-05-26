"""Read queries used by the CLI and the API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from pulse.db import AlertEventRow, AlertStateRow, CheckRecord, session_scope


@dataclass(frozen=True, slots=True)
class ServiceSummary:
    url: str
    total_checks: int
    successful_checks: int
    uptime_pct: float
    avg_latency_ms: float | None
    last_checked_at: datetime | None


@dataclass(frozen=True, slots=True)
class OverallStats:
    """Aggregate counts across the whole database."""

    services_tracked: int
    total_checks: int
    successful_checks: int
    overall_uptime_pct: float
    first_checked_at: datetime | None
    last_checked_at: datetime | None
    alerts_fired: int
    alerts_recovered: int
    active_alerts: int


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
    total = (
        session.scalar(select(func.count()).select_from(CheckRecord).where(CheckRecord.url == url))
        or 0
    )

    successful = (
        session.scalar(
            select(func.count())
            .select_from(CheckRecord)
            .where(CheckRecord.url == url, CheckRecord.ok.is_(True))
        )
        or 0
    )

    avg_latency = session.scalar(
        select(func.avg(CheckRecord.latency_ms)).where(
            CheckRecord.url == url, CheckRecord.ok.is_(True)
        )
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


def get_overall_stats(session: Session) -> OverallStats:
    """Compute aggregate stats across all services. Caller manages the session."""
    total = session.scalar(select(func.count()).select_from(CheckRecord)) or 0
    successful = (
        session.scalar(
            select(func.count()).select_from(CheckRecord).where(CheckRecord.ok.is_(True))
        )
        or 0
    )
    first = session.scalar(select(func.min(CheckRecord.checked_at)))
    last = session.scalar(select(func.max(CheckRecord.checked_at)))
    services = session.scalar(select(func.count(func.distinct(CheckRecord.url)))) or 0
    fired = (
        session.scalar(
            select(func.count()).select_from(AlertEventRow).where(AlertEventRow.kind == "failing")
        )
        or 0
    )
    recovered = (
        session.scalar(
            select(func.count()).select_from(AlertEventRow).where(AlertEventRow.kind == "recovered")
        )
        or 0
    )
    active = (
        session.scalar(
            select(func.count()).select_from(AlertStateRow).where(AlertStateRow.active.is_(True))
        )
        or 0
    )

    return OverallStats(
        services_tracked=services,
        total_checks=total,
        successful_checks=successful,
        overall_uptime_pct=(100.0 * successful / total) if total else 0.0,
        first_checked_at=first,
        last_checked_at=last,
        alerts_fired=fired,
        alerts_recovered=recovered,
        active_alerts=active,
    )


def get_recent_alerts(session: Session, limit: int = 10) -> list[AlertEventRow]:
    """Most recent alert events, newest first."""
    stmt = select(AlertEventRow).order_by(AlertEventRow.occurred_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars())


def prune_older_than(engine: Engine, days: int) -> int:
    """Delete CheckRecord rows older than `days` days. Returns rows deleted."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with session_scope(engine) as session:
        result = session.execute(delete(CheckRecord).where(CheckRecord.checked_at < cutoff))
        return getattr(result, "rowcount", 0) or 0


def prune_keep_last_per_service(engine: Engine, keep: int) -> int:
    """Per URL, keep only the most recent `keep` rows. Returns total deleted."""
    deleted = 0
    with session_scope(engine) as session:
        urls = session.scalars(select(CheckRecord.url).distinct()).all()
        for url in urls:
            ids_to_keep = session.scalars(
                select(CheckRecord.id)
                .where(CheckRecord.url == url)
                .order_by(CheckRecord.checked_at.desc())
                .limit(keep)
            ).all()
            if not ids_to_keep:
                continue
            result = session.execute(
                delete(CheckRecord).where(
                    CheckRecord.url == url,
                    CheckRecord.id.notin_(ids_to_keep),
                )
            )
            deleted += getattr(result, "rowcount", 0) or 0
    return deleted
