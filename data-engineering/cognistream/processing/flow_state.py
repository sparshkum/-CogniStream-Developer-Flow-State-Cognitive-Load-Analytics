"""Core Week-3 logic: turn raw IDE heartbeats + interruption events into
"Uninterrupted Flow Blocks" and the headline "Context-Switching Tax" metric.

Pipeline:
  1. `compute_coding_sessions` merges ActivityWatch heartbeats into continuous
     coding sessions (a gap longer than `idle_gap_tolerance_minutes` -- a
     meeting, lunch, end of day -- starts a new session).
  2. `compute_flow_blocks` splits each session at every external interruption
     event (Slack message/mention, Jira ticket ping, GitHub review request)
     that lands inside it, producing the sub-blocks the project spec calls
     "Uninterrupted Flow Blocks". A block counts as genuine deep flow once it
     reaches `flow_block_min_minutes` (default 90) with zero interruptions.
  3. `compute_daily_metrics` rolls blocks up into the per-developer/day
     Context-Switching Tax: the share of coding time that never made it into
     a 90+ minute flow block because an external notification cut it short.
"""
from __future__ import annotations

from datetime import datetime

import polars as pl

from cognistream.config import PIPELINE
from cognistream.schemas import NON_INTERRUPTING_EVENT_TYPES, Source


def compute_coding_sessions(events: pl.DataFrame, idle_gap_tolerance_minutes: float | None = None) -> pl.DataFrame:
    """Merge ActivityWatch IDE heartbeats into continuous coding sessions.

    A new session starts whenever the gap since the previous heartbeat ended
    exceeds `idle_gap_tolerance_minutes` -- i.e. the developer was away from
    the keyboard long enough that it's a real break, not a thinking pause.
    """
    tolerance = idle_gap_tolerance_minutes if idle_gap_tolerance_minutes is not None else PIPELINE.idle_gap_tolerance_minutes

    aw = events.filter(pl.col("source") == Source.ACTIVITYWATCH).sort(["developer", "event_time"])
    if aw.height == 0:
        return pl.DataFrame(
            schema={
                "developer": pl.Utf8,
                "team": pl.Utf8,
                "session_id": pl.Int64,
                "session_start": pl.Datetime(time_unit="us", time_zone="UTC"),
                "session_end": pl.Datetime(time_unit="us", time_zone="UTC"),
            }
        )

    aw = aw.with_columns((pl.col("event_time") + pl.duration(seconds=pl.col("duration_seconds"))).alias("event_end"))
    aw = aw.with_columns(pl.col("event_end").shift(1).over("developer").alias("prev_end"))
    aw = aw.with_columns(((pl.col("event_time") - pl.col("prev_end")).dt.total_seconds() / 60.0).alias("gap_minutes"))
    aw = aw.with_columns((pl.col("gap_minutes").is_null() | (pl.col("gap_minutes") > tolerance)).alias("new_session"))
    aw = aw.with_columns(pl.col("new_session").cast(pl.Int64).cum_sum().over("developer").alias("session_id"))

    sessions = (
        aw.group_by(["developer", "team", "session_id"])
        .agg(pl.col("event_time").min().alias("session_start"), pl.col("event_end").max().alias("session_end"))
        .sort(["developer", "session_start"])
    )
    return sessions


def _interruption_events(events: pl.DataFrame) -> pl.DataFrame:
    return events.filter(
        (pl.col("source") != Source.ACTIVITYWATCH) & (~pl.col("event_type").is_in(list(NON_INTERRUPTING_EVENT_TYPES)))
    ).select(["developer", "event_time", "source", "event_type"])


def compute_flow_blocks(
    events: pl.DataFrame,
    flow_block_min_minutes: float | None = None,
    idle_gap_tolerance_minutes: float | None = None,
) -> pl.DataFrame:
    """Split every coding session at each interruption event inside it,
    returning one row per resulting sub-block.
    """
    flow_min = flow_block_min_minutes if flow_block_min_minutes is not None else PIPELINE.flow_block_min_minutes
    sessions = compute_coding_sessions(events, idle_gap_tolerance_minutes)

    empty_schema = {
        "developer": pl.Utf8,
        "team": pl.Utf8,
        "date": pl.Utf8,
        "block_start": pl.Datetime(time_unit="us", time_zone="UTC"),
        "block_end": pl.Datetime(time_unit="us", time_zone="UTC"),
        "duration_minutes": pl.Float64,
        "is_flow_block": pl.Boolean,
        "interrupted_by": pl.Utf8,
    }
    if sessions.height == 0:
        return pl.DataFrame(schema=empty_schema)

    interruptions = _interruption_events(events)
    joined = (
        interruptions.join(sessions, on="developer", how="inner")
        .filter((pl.col("event_time") >= pl.col("session_start")) & (pl.col("event_time") <= pl.col("session_end")))
        .with_columns(pl.struct(["event_time", "source", "event_type"]).alias("interrupt"))
        .group_by(["developer", "team", "session_id", "session_start", "session_end"])
        .agg(pl.col("interrupt").sort_by("event_time").alias("interrupts"))
    )

    merged = sessions.join(
        joined.select(["developer", "session_id", "interrupts"]), on=["developer", "session_id"], how="left"
    )

    rows: list[dict] = []
    for row in merged.iter_rows(named=True):
        start: datetime = row["session_start"]
        end: datetime = row["session_end"]
        interrupts = row["interrupts"] or []
        cursor = start
        pieces: list[tuple[datetime, datetime, str | None]] = []
        for interrupt in interrupts:
            split_at = interrupt["event_time"]
            if split_at <= cursor:
                continue
            pieces.append((cursor, split_at, f"{interrupt['source']}:{interrupt['event_type']}"))
            cursor = split_at
        pieces.append((cursor, end, None))

        for block_start, block_end, interrupted_by in pieces:
            duration_minutes = (block_end - block_start).total_seconds() / 60.0
            if duration_minutes <= 0:
                continue
            rows.append(
                {
                    "developer": row["developer"],
                    "team": row["team"],
                    "date": block_start.strftime("%Y-%m-%d"),
                    "block_start": block_start,
                    "block_end": block_end,
                    "duration_minutes": round(duration_minutes, 2),
                    "is_flow_block": duration_minutes >= flow_min,
                    "interrupted_by": interrupted_by,
                }
            )

    if not rows:
        return pl.DataFrame(schema=empty_schema)

    return pl.DataFrame(rows, schema_overrides={"block_start": empty_schema["block_start"], "block_end": empty_schema["block_end"]}).sort(
        ["developer", "block_start"]
    )


def compute_daily_metrics(flow_blocks: pl.DataFrame, events: pl.DataFrame) -> pl.DataFrame:
    """Roll flow blocks up into the headline per-developer/day metrics that
    power the dashboard: total coding time, time spent in genuine flow,
    and the Context-Switching Tax this costs each developer.
    """
    if flow_blocks.height == 0:
        return pl.DataFrame(
            schema={
                "developer": pl.Utf8,
                "team": pl.Utf8,
                "date": pl.Utf8,
                "total_coding_minutes": pl.Float64,
                "flow_minutes": pl.Float64,
                "interrupted_minutes": pl.Float64,
                "context_switch_tax_pct": pl.Float64,
                "num_flow_blocks": pl.Int64,
                "longest_flow_block_minutes": pl.Float64,
                "num_interruptions_breaking_flow": pl.Int64,
                "total_interruption_events": pl.Int64,
                "total_commits": pl.Int64,
            }
        )

    daily = flow_blocks.group_by(["developer", "team", "date"]).agg(
        pl.col("duration_minutes").sum().alias("total_coding_minutes"),
        pl.col("duration_minutes").filter(pl.col("is_flow_block")).sum().alias("flow_minutes"),
        pl.col("is_flow_block").sum().alias("num_flow_blocks"),
        pl.col("duration_minutes").max().alias("longest_flow_block_minutes"),
        pl.col("interrupted_by").is_not_null().sum().alias("num_interruptions_breaking_flow"),
    )
    daily = daily.with_columns(pl.col("flow_minutes").fill_null(0.0))
    daily = daily.with_columns((pl.col("total_coding_minutes") - pl.col("flow_minutes")).alias("interrupted_minutes"))
    daily = daily.with_columns(
        pl.when(pl.col("total_coding_minutes") > 0)
        .then(pl.col("interrupted_minutes") / pl.col("total_coding_minutes") * 100)
        .otherwise(0.0)
        .round(2)
        .alias("context_switch_tax_pct")
    )

    events_with_date = events.with_columns(pl.col("event_time").dt.strftime("%Y-%m-%d").alias("date"))

    commits = (
        events_with_date.filter((pl.col("source") == Source.GITHUB) & (pl.col("event_type") == "commit"))
        .group_by(["developer", "date"])
        .agg(pl.len().alias("total_commits"))
    )
    interruption_events = _interruption_events(events).with_columns(pl.col("event_time").dt.strftime("%Y-%m-%d").alias("date"))
    all_interruptions = interruption_events.group_by(["developer", "date"]).agg(pl.len().alias("total_interruption_events"))

    daily = daily.join(commits, on=["developer", "date"], how="left").join(all_interruptions, on=["developer", "date"], how="left")
    daily = daily.with_columns(pl.col("total_commits").fill_null(0), pl.col("total_interruption_events").fill_null(0))

    return daily.sort(["date", "team", "developer"])
