"""Background async loop that checks services on a schedule."""
import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from .checker import check_many
from .db import init_db, record_to_row, session_scope
from .logging import get_logger
from .models import CheckResult

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


log = get_logger(__name__)


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
        log.info("monitor.round.starting", url_count=len(urls))
        results = await check_many(urls)
        ok_count = sum(1 for r in results if r.ok)
        log.info(
            "monitor.round.completed",
            url_count=len(urls),
            ok_count=ok_count,
            failed_count=len(urls) - ok_count,
        )

        with session_scope(engine) as session:
            for result in results:
                session.add(record_to_row(result))

        if on_round is not None:
            on_round(results)

        completed += 1
        if rounds is not None and completed >= rounds:
            return

        await asyncio.sleep(interval_seconds)