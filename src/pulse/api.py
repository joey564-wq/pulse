"""FastAPI application for Pulse."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.orm import Session

from pulse.db import init_db, make_engine, session_scope
from pulse.queries import get_history, list_service_urls

DB_PATH = Path("pulse.db")


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


def get_session(request: Request) -> Iterator[Session]:
    engine = request.app.state.engine
    with session_scope(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/services")
def services(session: SessionDep) -> list[str]:
    return list_service_urls(session)


@app.get("/history")
def history(url: str, session: SessionDep, limit: int = 100) -> list[dict]:
    records = get_history(session, url, limit=limit)
    return [
        {
            "url": r.url,
            "ok": r.ok,
            "status": r.status,
            "latency_ms": r.latency_ms,
            "error": r.error,
            "checked_at": r.checked_at.isoformat(),
        }
        for r in records
    ]