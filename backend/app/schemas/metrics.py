from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    developer_count: int
    total_commits: int
    total_hours_worked: float
    avg_context_switch_tax_pct: float
    total_interruptions: int
    total_flow_blocks: int
    avg_flow_block_minutes: float


class ContextSwitchTaxRow(BaseModel):
    developer: str
    team: str
    flow_minutes: float
    interrupted_minutes: float
    total_coding_minutes: float
    context_switch_tax_pct: float


class InterruptionSourceRow(BaseModel):
    source: str
    count: int
    pct: float


class FlowBlockRow(BaseModel):
    developer: str
    team: str
    date: str
    block_start: datetime
    block_end: datetime
    duration_minutes: float
    interrupted_by: str | None = None


class FlowTimelineBlock(BaseModel):
    block_start: datetime
    block_end: datetime
    duration_minutes: float
    is_flow_block: bool
    interrupted_by: str | None = None
