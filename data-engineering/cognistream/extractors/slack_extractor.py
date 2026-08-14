"""Mock Slack extractor.

Shapes its output after the real Slack Web API `conversations.history` /
`search.messages` response: https://api.slack.com/methods/conversations.history
Timestamps use Slack's native "ts" format (seconds.microseconds as a string).
"""
from __future__ import annotations

from cognistream.extractors import mock_world
from cognistream.extractors.base import write_raw_payload


def _message_payload(developer: str, team: str, interruption: "mock_world.InterruptionEvent") -> dict:
    meta = interruption.metadata
    ts = f"{interruption.timestamp.timestamp():.6f}"
    text = (
        f"<@{developer}> can you take a look at this when you get a sec?"
        if meta["kind"] == "mention"
        else "quick question about the deploy"
    )
    return {
        "type": "message",
        "subtype": None,
        "channel": meta["channel"],
        "user": meta["sender"],
        "text": text,
        "ts": ts,
        "_cognistream": {
            "recipient": developer,
            "team": team,
            "is_mention": meta["kind"] == "mention",
        },
    }


def extract_recent(days: int = 14) -> dict[str, list[dict]]:
    world = mock_world.build_world(days=days)
    by_date: dict[str, list[dict]] = {}
    for developer, day_plans in world.items():
        for plan in day_plans:
            bucket = by_date.setdefault(plan.date, [])
            for interruption in plan.interruptions:
                if interruption.source == "slack":
                    bucket.append(_message_payload(developer, plan.team, interruption))
    return by_date


def extract_for_date(run_date: str, days: int = 14) -> list[dict]:
    return extract_recent(days=days).get(run_date, [])


def run(run_date: str | None = None, days: int = 14) -> str:
    from cognistream.extractors.base import utcnow_run_date

    run_date = run_date or utcnow_run_date()
    payload = extract_for_date(run_date, days=days)
    return write_raw_payload("slack", run_date, payload)


if __name__ == "__main__":
    for date, payload in extract_recent().items():
        write_raw_payload("slack", date, payload)
    print("Slack mock extraction complete.")
