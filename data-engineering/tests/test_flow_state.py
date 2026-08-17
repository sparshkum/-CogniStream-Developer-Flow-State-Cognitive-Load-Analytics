from datetime import datetime, timedelta, timezone

import polars as pl

from cognistream.processing.clean import CANONICAL_SCHEMA
from cognistream.processing.flow_state import compute_coding_sessions, compute_daily_metrics, compute_flow_blocks

UTC = timezone.utc


def _events_df(rows: list[dict]) -> pl.DataFrame:
    defaults = {"event_id": "e", "duration_seconds": 0.0, "metadata": "{}"}
    full_rows = [{**defaults, **row} for row in rows]
    return pl.DataFrame(full_rows, schema_overrides={"event_time": CANONICAL_SCHEMA["event_time"]})


def test_uninterrupted_100_minute_session_is_one_flow_block():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    heartbeats = [
        {
            "developer": "alice",
            "team": "Team A",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(20)  # 20 * 5min = 100 minutes, contiguous
    ]
    events = _events_df(heartbeats)

    blocks = compute_flow_blocks(events, flow_block_min_minutes=90, idle_gap_tolerance_minutes=10)
    assert blocks.height == 1
    row = blocks.row(0, named=True)
    assert row["is_flow_block"] is True
    assert row["interrupted_by"] is None
    assert row["duration_minutes"] >= 99


def test_slack_message_mid_session_splits_the_block_and_breaks_flow():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    heartbeats = [
        {
            "developer": "bob",
            "team": "Team A",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(20)  # still 100 contiguous minutes of heartbeats
    ]
    interruption = {
        "developer": "bob",
        "team": "Team A",
        "source": "slack",
        "event_type": "mention_received",
        "event_time": start + timedelta(minutes=50),  # lands mid-session
    }
    events = _events_df(heartbeats + [interruption])

    blocks = compute_flow_blocks(events, flow_block_min_minutes=90, idle_gap_tolerance_minutes=10)
    assert blocks.height == 2, "the interruption should split one session into two sub-blocks"
    assert not blocks["is_flow_block"].any(), "neither 50-minute half should qualify as a 90-minute flow block"
    assert blocks.filter(pl.col("interrupted_by").is_not_null()).height == 1
    assert blocks.row(0, named=True)["interrupted_by"] == "slack:mention_received"


def test_large_idle_gap_starts_a_new_session_without_an_event():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    morning = [
        {
            "developer": "carla",
            "team": "Team B",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(12)  # 60 minutes
    ]
    afternoon_start = start + timedelta(hours=3)  # 2-hour gap -- lunch, no event
    afternoon = [
        {
            "developer": "carla",
            "team": "Team B",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": afternoon_start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(12)
    ]
    events = _events_df(morning + afternoon)
    sessions = compute_coding_sessions(events, idle_gap_tolerance_minutes=10)
    assert sessions.height == 2


def test_commit_events_never_count_as_interruptions():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    heartbeats = [
        {
            "developer": "dinesh",
            "team": "Team B",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(20)
    ]
    commit = {
        "developer": "dinesh",
        "team": "Team B",
        "source": "github",
        "event_type": "commit",
        "event_time": start + timedelta(minutes=50),
    }
    events = _events_df(heartbeats + [commit])
    blocks = compute_flow_blocks(events, flow_block_min_minutes=90, idle_gap_tolerance_minutes=10)
    assert blocks.height == 1, "a commit is coding output, not an external interruption, and must not split the block"


def test_daily_metrics_context_switch_tax_matches_manual_calculation():
    start = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    heartbeats = [
        {
            "developer": "elena",
            "team": "Team B",
            "source": "activitywatch",
            "event_type": "ide_active",
            "event_time": start + timedelta(minutes=i * 5),
            "duration_seconds": 300.0,
        }
        for i in range(24)  # 120 contiguous minutes
    ]
    interruption = {
        "developer": "elena",
        "team": "Team B",
        "source": "jira",
        "event_type": "ticket_transitioned",
        "event_time": start + timedelta(minutes=40),  # splits into a 40-min block and an 80-min block
    }
    events = _events_df(heartbeats + [interruption])
    blocks = compute_flow_blocks(events, flow_block_min_minutes=90, idle_gap_tolerance_minutes=10)
    daily = compute_daily_metrics(blocks, events)

    assert daily.height == 1
    row = daily.row(0, named=True)
    assert row["total_coding_minutes"] == blocks["duration_minutes"].sum()
    # Neither the 40-min nor the 80-min piece reaches the 90-min flow threshold.
    assert row["flow_minutes"] == 0.0
    assert row["context_switch_tax_pct"] == 100.0
    assert row["num_interruptions_breaking_flow"] == 1
