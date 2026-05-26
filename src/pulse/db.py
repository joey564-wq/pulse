"""SQLAlchemy database layer for Pulse."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import CheckResult


class Base(DeclarativeBase):
    """Shared base for all ORM models."""


class CheckRecord(Base):
    """A row in the check_records table — one historical check outcome."""

    __tablename__ = "check_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(index=True)
    status: Mapped[int | None]
    ok: Mapped[bool]
    latency_ms: Mapped[float]
    error: Mapped[str | None]
    checked_at: Mapped[datetime] = mapped_column(index=True)


class AlertStateRow(Base):
    """Current alert state for one URL. One row per service ever observed."""

    __tablename__ = "alert_state"

    url: Mapped[str] = mapped_column(primary_key=True)
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=False)
    last_event_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AlertEventRow(Base):
    """One alert lifecycle event: a fire or a recovery."""

    __tablename__ = "alert_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(index=True)
    kind: Mapped[str]  # "failing" | "recovered"
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    consecutive_failures: Mapped[int]


def make_engine(db_path: Path | str) -> Engine:
    """Create a SQLAlchemy engine pointed at a SQLite file (or ':memory:')."""
    if str(db_path) == ":memory:":
        url = "sqlite:///:memory:"
    else:
        # Three slashes + relative path, or four for an absolute path.
        url = f"sqlite:///{Path(db_path).resolve()}"
    return create_engine(url, echo=False)


def init_db(engine: Engine) -> None:
    """Create all tables. Safe to call repeatedly — it's CREATE IF NOT EXISTS."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Yield a session, commit on success, rollback on error, always close."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def record_to_row(result: CheckResult) -> CheckRecord:
    """Convert a Pydantic CheckResult into an ORM row ready for the DB."""
    return CheckRecord(**result.model_dump())
