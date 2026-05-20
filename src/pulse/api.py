"""FastAPI application for Pulse."""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Pulse",
    description="Service health monitor",
    version="0.3.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check. Doesn't touch the DB."""
    return {"status": "ok"}