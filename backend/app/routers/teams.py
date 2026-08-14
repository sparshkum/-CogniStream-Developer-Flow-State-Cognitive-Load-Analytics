from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_ch_service
from app.services.clickhouse_service import ClickHouseService

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams")
def get_teams(ch: ClickHouseService = Depends(get_ch_service)) -> list[str]:
    return ch.list_teams()


@router.get("/developers")
def get_developers(team: str | None = None, ch: ClickHouseService = Depends(get_ch_service)) -> list[str]:
    return ch.list_developers(team)
