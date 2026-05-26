"""FastAPI application for Pulse."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from pulse.db import AlertEventRow, CheckRecord, init_db, make_engine, session_scope
from pulse.queries import (
    OverallStats,
    ServiceSummary,
    get_all_summaries,
    get_history,
    get_overall_stats,
    get_recent_alerts,
    get_summary,
    list_service_urls,
)
from pulse.schemas import (
    AlertEventOut,
    CheckRecordOut,
    OverallStatsOut,
    ServiceSummaryOut,
)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Resolved at startup, not at import time, so `pulse serve --db ...`
    # and `pulse demo` can override via the PULSE_DB env var.
    db_path = Path(os.environ.get("PULSE_DB", "pulse.db"))
    engine = make_engine(db_path)
    init_db(engine)
    app.state.engine = engine
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Pulse",
    description="Service health monitor",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_session(request: Request) -> Iterator[Session]:
    engine = request.app.state.engine
    with session_scope(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/")
async def index() -> FileResponse:
    """Serve the dashboard HTML page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/services")
def services(session: SessionDep) -> list[str]:
    return list_service_urls(session)


@app.get("/history", response_model=list[CheckRecordOut])
def history(url: str, session: SessionDep, limit: int = 100) -> list[CheckRecord]:
    return get_history(session, url, limit=limit)


@app.get("/summary", response_model=list[ServiceSummaryOut])
def summary(session: SessionDep) -> list[ServiceSummary]:
    return get_all_summaries(session)


@app.get("/summary/{url:path}", response_model=ServiceSummaryOut)
def summary_one(url: str, session: SessionDep) -> ServiceSummary:
    return get_summary(session, url)


@app.get("/stats", response_model=OverallStatsOut)
def stats(session: SessionDep) -> OverallStats:
    return get_overall_stats(session)


@app.get("/alerts/recent", response_model=list[AlertEventOut])
def alerts_recent(session: SessionDep, limit: int = 10) -> list[AlertEventRow]:
    return get_recent_alerts(session, limit=limit)
