"""End-to-end pipeline orchestration: extract -> clean -> flow-state -> load.

This module is the single source of truth for "what a pipeline run does".
Airflow DAG tasks (`airflow/dags/cognistream_pipeline_dag.py`) are thin
wrappers that call these functions, and so does the no-Airflow local runner
(`scripts/run_local_pipeline.py`) used for day-to-day development on a
machine without Docker/Airflow installed. Keeping the DAG file free of real
logic means the pipeline can be fully unit-tested without an Airflow install.
"""
from __future__ import annotations

import logging
import os

import polars as pl

from cognistream.config import PIPELINE
from cognistream.extractors import activitywatch_extractor, github_extractor, jira_extractor, slack_extractor
from cognistream.processing import clean, flow_state
from cognistream.storage import loader
from cognistream.storage.clickhouse_client import bootstrap_schema, get_client

logger = logging.getLogger("cognistream.pipeline")

EXTRACTORS = {
    "github": github_extractor,
    "slack": slack_extractor,
    "jira": jira_extractor,
    "activitywatch": activitywatch_extractor,
}


def extract_day(run_date: str, days_context: int = 14) -> dict[str, list[dict]]:
    """Run all four mock extractors for a single run_date and write raw JSON
    to the landing zone. `days_context` controls how many trailing workdays
    the underlying behavioral simulation considers -- it does not change how
    many days get written, only how much history the (deterministic) mock
    world simulates before slicing out `run_date`.
    """
    from cognistream.extractors.base import write_raw_payload

    raw_by_source: dict[str, list[dict]] = {}
    for source, extractor in EXTRACTORS.items():
        payload = extractor.extract_for_date(run_date, days=days_context)
        path = write_raw_payload(source, run_date, payload)
        raw_by_source[source] = payload
        logger.info("extracted %d %s events for %s -> %s", len(payload), source, run_date, path)
    return raw_by_source


def clean_day(run_date: str) -> pl.DataFrame:
    events = clean.clean_date(run_date)
    clean.write_clean_parquet(run_date, events)
    logger.info("cleaned %d events for %s", events.height, run_date)
    return events


def _intermediate_path(kind: str, run_date: str) -> str:
    return os.path.join(PIPELINE.clean_data_dir, kind, f"{run_date}.parquet")


def compute_flow_state(run_date: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Read the day's cleaned events (written by `clean_day`), compute flow
    blocks + daily metrics, and persist both to parquet so a downstream
    Airflow task can load them into ClickHouse without passing DataFrames
    through XCom.
    """
    events = clean.read_clean_parquet(run_date)
    blocks = flow_state.compute_flow_blocks(events)
    daily = flow_state.compute_daily_metrics(blocks, events)

    blocks_path = _intermediate_path("flow_blocks", run_date)
    daily_path = _intermediate_path("daily_metrics", run_date)
    os.makedirs(os.path.dirname(blocks_path), exist_ok=True)
    os.makedirs(os.path.dirname(daily_path), exist_ok=True)
    blocks.write_parquet(blocks_path)
    daily.write_parquet(daily_path)

    logger.info("computed %d flow blocks across %d developer-days for %s", blocks.height, daily.height, run_date)
    return blocks, daily


def load_to_clickhouse(run_date: str) -> dict[str, int]:
    """Read the parquet artifacts written by `clean_day`/`compute_flow_state`
    for `run_date` and load them into ClickHouse, replacing any existing rows
    for that date so re-running a day's pipeline is idempotent.
    """
    events = clean.read_clean_parquet(run_date)
    blocks = pl.read_parquet(_intermediate_path("flow_blocks", run_date))
    daily = pl.read_parquet(_intermediate_path("daily_metrics", run_date))

    client = get_client()
    bootstrap_schema(client)

    loader.delete_date_range(client, loader.EVENTS_TABLE, "event_date", run_date, run_date)
    loader.delete_date_range(client, loader.FLOW_BLOCKS_TABLE, "date", run_date, run_date)
    loader.delete_date_range(client, loader.DAILY_METRICS_TABLE, "date", run_date, run_date)

    counts = {
        "events": loader.load_events(events, client),
        "flow_blocks": loader.load_flow_blocks(blocks, client),
        "daily_metrics": loader.load_daily_metrics(daily, client),
    }
    logger.info("loaded into ClickHouse for %s: %s", run_date, counts)
    return counts


def run_pipeline_for_date(run_date: str, days_context: int = 14, load: bool = True) -> dict:
    """Run the full extract -> clean -> flow-state -> (optionally) load
    pipeline for one calendar date. Returns a summary dict for logging/DAG
    XCom or CLI printing. Mirrors exactly what the Airflow DAG's four tasks
    do in sequence, for use by the no-Airflow local runner.
    """
    extract_day(run_date, days_context=days_context)
    events = clean_day(run_date)
    blocks, daily = compute_flow_state(run_date)

    summary = {
        "run_date": run_date,
        "events": events.height,
        "flow_blocks": blocks.height,
        "developer_days": daily.height,
    }
    if load:
        summary["loaded"] = load_to_clickhouse(run_date)
    return summary
