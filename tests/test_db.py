from datetime import UTC, datetime

from pulse.db import CheckRecord, init_db, make_engine, record_to_row, session_scope
from pulse.models import CheckResult


def test_record_and_read_back():
    engine = make_engine(":memory:")
    init_db(engine)

    result = CheckResult(
        url="https://example.com",
        status=200,
        ok=True,
        latency_ms=42.5,
        checked_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    with session_scope(engine) as session:
        session.add(record_to_row(result))

    with session_scope(engine) as session:
        rows = session.query(CheckRecord).all()

    assert len(rows) == 1
    assert rows[0].url == "https://example.com"
    assert rows[0].status == 200
    assert rows[0].ok is True
    assert rows[0].latency_ms == 42.5
