"""Load cleaned events / flow blocks / daily metrics Polars DataFrames into
ClickHouse. This is the last step of the Week 2 "clean -> load" pipeline and
the Week 3 "persist computed flow blocks" step.
"""
from __future__ import annotations

import polars as pl
from clickhouse_connect.driver.client import Client

from cognistream.storage.clickhouse_client import get_client

EVENTS_TABLE = "cognistream.events"
FLOW_BLOCKS_TABLE = "cognistream.flow_blocks"
DAILY_METRICS_TABLE = "cognistream.daily_metrics"


def _insert(client: Client, table: str, df: pl.DataFrame) -> int:
    if df.height == 0:
        return 0
    client.insert(table, df.rows(), column_names=df.columns)
    return df.height


def load_events(df: pl.DataFrame, client: Client | None = None) -> int:
    client = client or get_client()
    return _insert(client, EVENTS_TABLE, df)


def load_flow_blocks(df: pl.DataFrame, client: Client | None = None) -> int:
    client = client or get_client()
    cols = ["developer", "team", "date", "block_start", "block_end", "duration_minutes", "is_flow_block", "interrupted_by"]
    df = df.select(cols).with_columns(pl.col("date").str.to_date(), pl.col("is_flow_block").cast(pl.UInt8))
    return _insert(client, FLOW_BLOCKS_TABLE, df)


def load_daily_metrics(df: pl.DataFrame, client: Client | None = None) -> int:
    client = client or get_client()
    df = df.with_columns(pl.col("date").str.to_date())
    return _insert(client, DAILY_METRICS_TABLE, df)


def delete_date_range(client: Client, table: str, date_column: str, start_date: str, end_date: str) -> None:
    """Idempotency helper: clear a date range before reloading it, so re-running
    the pipeline for a backfilled range doesn't duplicate rows (ClickHouse
    MergeTree has no unique-key upsert).
    """
    client.command(f"ALTER TABLE {table} DELETE WHERE {date_column} >= '{start_date}' AND {date_column} <= '{end_date}'")
