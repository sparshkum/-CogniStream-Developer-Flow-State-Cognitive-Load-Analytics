"""Mock Jira extractor.

Shapes its output after a real Jira issue-changelog / webhook payload:
https://developer.atlassian.com/cloud/jira/platform/webhooks/#example-callback-body
"""
from __future__ import annotations

from cognistream.extractors import mock_world
from cognistream.extractors.base import iso, write_raw_payload


def _changelog_payload(developer: str, team: str, interruption: "mock_world.InterruptionEvent") -> dict:
    meta = interruption.metadata
    is_transition = interruption.event_type == "ticket_transitioned"
    items = (
        [{"field": "status", "fromString": "To Do", "toString": meta["transition"]}]
        if is_transition
        else [{"field": "comment", "fromString": None, "toString": "New comment added"}]
    )
    return {
        "webhookEvent": "jira:issue_updated",
        "issue": {"key": meta["ticket"], "fields": {"assignee": {"name": developer}}},
        "changelog": {"items": items},
        "user": {"displayName": "eng_manager"},
        "timestamp": iso(interruption.timestamp),
        "_cognistream": {"team": team, "assignee": developer},
    }


def extract_recent(days: int = 14) -> dict[str, list[dict]]:
    world = mock_world.build_world(days=days)
    by_date: dict[str, list[dict]] = {}
    for developer, day_plans in world.items():
        for plan in day_plans:
            bucket = by_date.setdefault(plan.date, [])
            for interruption in plan.interruptions:
                if interruption.source == "jira":
                    bucket.append(_changelog_payload(developer, plan.team, interruption))
    return by_date


def extract_for_date(run_date: str, days: int = 14) -> list[dict]:
    return extract_recent(days=days).get(run_date, [])


def run(run_date: str | None = None, days: int = 14) -> str:
    from cognistream.extractors.base import utcnow_run_date

    run_date = run_date or utcnow_run_date()
    payload = extract_for_date(run_date, days=days)
    return write_raw_payload("jira", run_date, payload)


if __name__ == "__main__":
    for date, payload in extract_recent().items():
        write_raw_payload("jira", date, payload)
    print("Jira mock extraction complete.")
