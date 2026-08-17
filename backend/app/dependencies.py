from __future__ import annotations

from fastapi import Request

from app.services.clickhouse_service import ClickHouseService


def get_ch_service(request: Request) -> ClickHouseService:
    return request.app.state.ch_service
