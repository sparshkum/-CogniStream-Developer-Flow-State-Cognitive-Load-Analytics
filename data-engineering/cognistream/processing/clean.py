"""Normalize raw GitHub / Slack / Jira / ActivityWatch JSON payloads into the
single canonical event schema (`cognistream.schemas.CanonicalEvent`), using
Polars for the heavy lifting. This is the Week 2 "clean the extracted JSON
payloads" step from the project plan.

Each `parse_*` function turns one source's raw, API-shaped JSON into a list
of flat dicts. `clean_events` concatenates all four into a single typed
Polars DataFrame ready to load into ClickHouse.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import polars as pl

from cognistream.config import PIPELINE
from cognistream.schemas import EventType, Source

CANONICAL_SCHEMA = {
    "event_id": pl.Utf8,
    "developer": pl.Utf8,
    "team": pl.Utf8,
    "source": pl.Utf8,
    "event_type": pl.Utf8,
    "event_time": pl.Datetime(time_unit="us", time_zone="UTC"),
    "duration_seconds": pl.Float64,
    "metadata": pl.Utf8,
}


def _parse_ts(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _row(developer: str, source: str, event_type: str, event_time: datetime, duration_seconds: float, metadata: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "developer": developer,
        "team": PIPELINE.team_for(developer),
        "source": source,
        "event_type": event_type,
        "event_time": event_time,
        "duration_seconds": float(duration_seconds),
        "metadata": json.dumps(metadata, default=str),
    }


def parse_github(raw_events: list[dict]) -> list[dict]:
    rows = []
    for raw in raw_events:
        if "commit" in raw:
            developer = raw["author"]["login"]
            rows.append(
                _row(
                    developer,
                    Source.GITHUB,
                    EventType.COMMIT,
                    _parse_ts(raw["commit"]["author"]["date"]),
                    0.0,
                    {"sha": raw["sha"], **raw.get("stats", {})},
                )
            )
        elif raw.get("action") == "review_requested":
            developer = raw["requested_reviewer"]["login"]
            rows.append(
                _row(
                    developer,
                    Source.GITHUB,
                    EventType.PR_REVIEW_REQUESTED,
                    _parse_ts(raw["pull_request"]["updated_at"]),
                    0.0,
                    {
                        "pr_number": raw["pull_request"]["number"],
                        "requested_by": raw["sender"]["login"],
                        "url": raw["pull_request"]["html_url"],
                    },
                )
            )
    return rows


def parse_slack(raw_events: list[dict]) -> list[dict]:
    rows = []
    for raw in raw_events:
        meta = raw["_cognistream"]
        event_type = EventType.MENTION_RECEIVED if meta["is_mention"] else EventType.MESSAGE_RECEIVED
        rows.append(
            _row(
                meta["recipient"],
                Source.SLACK,
                event_type,
                datetime.fromtimestamp(float(raw["ts"]), tz=timezone.utc),
                0.0,
                {"channel": raw["channel"], "sender": raw["user"], "text": raw["text"]},
            )
        )
    return rows


def parse_jira(raw_events: list[dict]) -> list[dict]:
    rows = []
    for raw in raw_events:
        developer = raw["issue"]["fields"]["assignee"]["name"]
        items = raw["changelog"]["items"]
        is_transition = any(item["field"] == "status" for item in items)
        event_type = EventType.TICKET_TRANSITIONED if is_transition else EventType.TICKET_COMMENTED
        metadata = {"ticket": raw["issue"]["key"]}
        if is_transition:
            metadata["transition"] = next(item["toString"] for item in items if item["field"] == "status")
        rows.append(
            _row(
                developer,
                Source.JIRA,
                event_type,
                _parse_ts(raw["timestamp"]),
                0.0,
                metadata,
            )
        )
    return rows


def parse_activitywatch(raw_events: list[dict]) -> list[dict]:
    rows = []
    for raw in raw_events:
        developer = raw["_cognistream"]["developer"]
        rows.append(
            _row(
                developer,
                Source.ACTIVITYWATCH,
                EventType.IDE_ACTIVE,
                _parse_ts(raw["timestamp"]),
                float(raw["duration"]),
                {"app": raw["data"]["app"], "title": raw["data"]["title"]},
            )
        )
    return rows


PARSERS = {
    Source.GITHUB: parse_github,
    Source.SLACK: parse_slack,
    Source.JIRA: parse_jira,
    Source.ACTIVITYWATCH: parse_activitywatch,
}


def clean_events(raw_by_source: dict[str, list[dict]]) -> pl.DataFrame:
    """Turn {"github": [...], "slack": [...], ...} raw payloads into one
    canonical Polars DataFrame, sorted by developer then event_time.
    """
    rows: list[dict] = []
    for source, raw_events in raw_by_source.items():
        parser = PARSERS.get(source)
        if parser is None:
            continue
        rows.extend(parser(raw_events))

    if not rows:
        return pl.DataFrame(schema=CANONICAL_SCHEMA)

    df = pl.DataFrame(rows, schema_overrides={"event_time": CANONICAL_SCHEMA["event_time"]})
    return df.sort(["developer", "event_time"])


def load_raw_json(source: str, run_date: str) -> list[dict]:
    path = os.path.join(PIPELINE.raw_data_dir, source, f"{run_date}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def clean_date(run_date: str) -> pl.DataFrame:
    """Load all four sources' raw JSON for `run_date` and return the cleaned,
    unified event DataFrame for that day.
    """
    raw_by_source = {source: load_raw_json(source, run_date) for source in PARSERS}
    return clean_events(raw_by_source)


def clean_parquet_path(run_date: str) -> str:
    return os.path.join(PIPELINE.clean_data_dir, "events", f"{run_date}.parquet")


def write_clean_parquet(run_date: str, df: pl.DataFrame | None = None) -> str:
    df = df if df is not None else clean_date(run_date)
    path = clean_parquet_path(run_date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.write_parquet(path)
    return path


def read_clean_parquet(run_date: str) -> pl.DataFrame:
    return pl.read_parquet(clean_parquet_path(run_date))
