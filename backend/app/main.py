from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import flow, metrics, teams
from app.services.clickhouse_service import ClickHouseService


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ch_service = ClickHouseService.connect()
    try:
        yield
    finally:
        app.state.ch_service.close()


app = FastAPI(
    title="CogniStream API",
    description="Serves aggregated developer flow-state & context-switching-tax metrics from ClickHouse.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(teams.router)
app.include_router(metrics.router)
app.include_router(flow.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
