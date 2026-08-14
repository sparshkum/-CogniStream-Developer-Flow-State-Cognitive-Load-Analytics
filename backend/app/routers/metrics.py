"""Aggregated ClickHouse metrics for the dashboard's summary cards and
charts. All date-range params default to the trailing 14 days so the
dashboard has a sensible view with zero query params.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_ch_service
from app.schemas.metrics import ContextSwitchTaxRow, FlowBlockRow, InterruptionSourceRow, SummaryResponse
from app.services.clickhouse_service import ClickHouseService

router = APIRouter(prefix="/api", tags=["metrics"])


def _default_range() -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=14)).isoformat(), today.isoformat()


def _resolve_range(date_from: str | None, date_to: str | None) -> tuple[str, str]:
    default_from, default_to = _default_range()
    return date_from or default_from, date_to or default_to


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    team: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ch: ClickHouseService = Depends(get_ch_service),
):
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return ch.summary(team, resolved_from, resolved_to)


@router.get("/context-switch-tax", response_model=list[ContextSwitchTaxRow])
def get_context_switch_tax(
    team: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ch: ClickHouseService = Depends(get_ch_service),
):
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return ch.context_switch_tax_by_developer(team, resolved_from, resolved_to)


@router.get("/interruptions-by-source", response_model=list[InterruptionSourceRow])
def get_interruptions_by_source(
    team: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ch: ClickHouseService = Depends(get_ch_service),
):
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return ch.interruptions_by_source(team, resolved_from, resolved_to)


@router.get("/flow-blocks", response_model=list[FlowBlockRow])
def get_flow_blocks(
    team: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    min_duration: float = 90,
    ch: ClickHouseService = Depends(get_ch_service),
):
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return ch.flow_blocks(team, resolved_from, resolved_to, min_duration)
