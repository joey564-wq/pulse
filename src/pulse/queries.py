"""Read queries used by the CLI and the API."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pulse.db import CheckRecord


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