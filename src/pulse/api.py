"""FastAPI application for Pulse."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from pulse.db import CheckRecord, init_db, make_engine, session_scope
from pulse.queries import (
    ServiceSummary,
    get_all_summaries,
    get_history,
    get_summary,
    list_service_urls,
)
from pulse.schemas import CheckRecordOut, ServiceSummaryOut

DB_PATH = Path("pulse.db")
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine(DB_PATH)
    init_db(engine)
    app.state.engine = engine
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title="Pulse",
    description="Service health monitor",
    version="0.3.0",
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