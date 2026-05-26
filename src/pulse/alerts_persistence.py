"""Bridge between the pure in-memory AlertTracker and the SQLite store.

The tracker stays pure — events in, events out, no I/O. This module is the
only place that touches both the tracker and the DB.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine

from .alerts import AlertEvent, AlertTracker
from .db import AlertEventRow, AlertStateRow, session_scope


def load_tracker(engine: Engine, tracker: AlertTracker) -> None:
    """Populate `tracker` from persisted state. Call once at monitor startup.

    Does not fire events — this is restoration, not observation.
    """
    with session_scope(engine) as session:
        for row in session.scalars(select(AlertStateRow)).all():
            tracker.hydrate(
                url=row.url,
                consecutive_failures=row.consecutive_failures,
                active=row.active,
            )


def persist_observation(
    engine: Engine,
    *,
    url: str,
    consecutive_failures: int,
    active: bool,
    event: AlertEvent | None,
) -> None:
    """Write current state for one URL, and append the event if one fired.

    `event` is the AlertEvent returned by `tracker.record(...)` for this
    observation, or None if no event fired this round.
    """
    with session_scope(engine) as session:
        row = session.get(AlertStateRow, url)
        if row is None:
            row = AlertStateRow(url=url)
            session.add(row)
        row.consecutive_failures = consecutive_failures
        row.active = active

        if event is not None:
            row.last_event_at = event.at
            session.add(
                AlertEventRow(
                    url=event.url,
                    kind=event.kind,
                    occurred_at=event.at,  # AlertEvent.at maps to AlertEventRow.occurred_at
                    consecutive_failures=event.consecutive_failures,
                )
            )
