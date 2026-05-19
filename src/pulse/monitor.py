"""Background async loop that checks services on a schedule."""
import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from .checker import check_many
from .db import init_db, record_to_row, session_scope
from .models import CheckResult

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


async def run_monitor(
    urls: list[str],
    engine: "Engine",
    interval_seconds: float = 30.0,
    on_round: Callable[[list[CheckResult]], None] | None = None,
    rounds: int | None = None,
) -> None:
    """Check all urls every interval_seconds, persisting each round.

    Parameters:
      - urls: services to check each round.
      - engine: SQLAlchemy engine (already created).
      - interval_seconds: sleep between rounds.
      - on_round: optional callback called after each round, useful for
        printing or for tests that want to inspect results.
      - rounds: if set, stop after this many rounds. If None, run forever.
    """
    init_db(engine)
    completed = 0
    while True:
        results = await check_many(urls)
        with session_scope(engine) as session:
            for result in results:
                session.add(record_to_row(result))
        if on_round is not None:
            on_round(results)

        completed += 1
        if rounds is not None and completed >= rounds:
            return

        await asyncio.sleep(interval_seconds)