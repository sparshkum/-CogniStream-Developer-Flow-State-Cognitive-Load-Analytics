"""Mock ActivityWatch (VSCode IDE activity) extractor.

Shapes its output after the real ActivityWatch REST API:
`GET /api/0/buckets/{bucket_id}/events` ->
[{"id": int, "timestamp": iso8601, "duration": seconds, "data": {"app":, "title":}}]
https://docs.activitywatch.net/en/latest/rest-api.html

This is the primary "is the developer actually coding" signal that
flow_state.py merges into continuous sessions.
"""
from __future__ import annotations

from cognistream.extractors import mock_world
from cognistream.extractors.base import iso, write_raw_payload


def _heartbeat_payload(event_id: int, developer: str, team: str, beat: "mock_world.IdeHeartbeat") -> dict:
    return {
        "id": event_id,
        "timestamp": iso(beat.timestamp),
        "duration": round(beat.duration_seconds, 3),
        "data": {"app": beat.app, "title": beat.window_title},
        "_cognistream": {"developer": developer, "team": team, "bucket_id": f"aw-watcher-window_{developer}"},
    }


def extract_recent(days: int = 14) -> dict[str, list[dict]]:
    world = mock_world.build_world(days=days)
    by_date: dict[str, list[dict]] = {}
    event_id = 0
    for developer, day_plans in world.items():
        for plan in day_plans:
            bucket = by_date.setdefault(plan.date, [])
            for beat in plan.heartbeats:
                event_id += 1
                bucket.append(_heartbeat_payload(event_id, developer, plan.team, beat))
    return by_date


def extract_for_date(run_date: str, days: int = 14) -> list[dict]:
    return extract_recent(days=days).get(run_date, [])


def run(run_date: str | None = None, days: int = 14) -> str:
    from cognistream.extractors.base import utcnow_run_date

    run_date = run_date or utcnow_run_date()
    payload = extract_for_date(run_date, days=days)
    return write_raw_payload("activitywatch", run_date, payload)


if __name__ == "__main__":
    for date, payload in extract_recent().items():
        write_raw_payload("activitywatch", date, payload)
    print("ActivityWatch mock extraction complete.")
