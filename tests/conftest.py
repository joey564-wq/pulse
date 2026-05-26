# tests/conftest.py
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from pulse.db import init_db, make_engine


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    """A throwaway file-backed SQLite engine for one test.

    File-backed (not :memory:) because FastAPI's TestClient runs sync
    handlers in a threadpool, and SQLite's default cross-thread check
    forbids that. A tmp_path file dodges the issue without needing
    connect_args={'check_same_thread': False}.
    """
    eng = make_engine(tmp_path / "test.db")
    init_db(eng)
    yield eng
    eng.dispose()
