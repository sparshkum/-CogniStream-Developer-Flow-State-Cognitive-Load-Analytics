from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_ch_service
from app.schemas.metrics import FlowTimelineBlock
from app.services.clickhouse_service import ClickHouseService

router = APIRouter(prefix="/api", tags=["flow"])


@router.get("/flow-timeline", response_model=list[FlowTimelineBlock])
def get_flow_timeline(
    developer: str = Query(...),
    date: str | None = Query(None),
    ch: ClickHouseService = Depends(get_ch_service),
):
    resolved_date = date or datetime.now(timezone.utc).date().isoformat()
    return ch.flow_timeline(developer, resolved_date)
