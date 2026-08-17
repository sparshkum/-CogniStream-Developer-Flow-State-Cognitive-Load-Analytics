"""Mock GitHub extractor.

Shapes its output after the real GitHub REST API:
- commits: https://docs.github.com/en/rest/commits/commits (list-commits shape)
- review requests: https://docs.github.com/en/webhooks (pull_request.review_requested)

A real extractor would call `GET /repos/{owner}/{repo}/commits?since=...` and
the GitHub webhook/events feed per developer; this mock reproduces the same
JSON envelope so `processing/clean.py` has to parse a realistic nested shape.
"""
from __future__ import annotations

from cognistream.extractors import mock_world
from cognistream.extractors.base import iso, write_raw_payload


def _commit_payload(developer: str, team: str, commit: "mock_world.CommitEvent") -> dict:
    sha = f"{abs(hash((developer, commit.timestamp))):012x}"
    return {
        "sha": sha,
        "commit": {
            "author": {"name": developer, "email": f"{developer}@cognistream.dev", "date": iso(commit.timestamp)},
            "message": f"Update {commit.metadata['lines_added']} lines across CogniStream modules",
        },
        "author": {"login": developer},
        "stats": {"additions": commit.metadata["lines_added"], "deletions": commit.metadata["lines_removed"]},
        "_cognistream": {"team": team},
    }


def _review_request_payload(developer: str, team: str, interruption: "mock_world.InterruptionEvent") -> dict:
    meta = interruption.metadata
    return {
        "action": "review_requested",
        "pull_request": {
            "number": meta["pr_number"],
            "title": f"COGNI-{meta['pr_number']}: platform changes",
            "html_url": f"https://github.com/cognistream/platform/pull/{meta['pr_number']}",
            "updated_at": iso(interruption.timestamp),
        },
        "requested_reviewer": {"login": developer},
        "sender": {"login": meta["requested_by"]},
        "_cognistream": {"team": team, "timestamp": iso(interruption.timestamp)},
    }


def extract_recent(days: int = 14) -> dict[str, list[dict]]:
    """Return {run_date: [raw github payload, ...]} for the last `days` workdays."""
    world = mock_world.build_world(days=days)
    by_date: dict[str, list[dict]] = {}
    for developer, day_plans in world.items():
        for plan in day_plans:
            bucket = by_date.setdefault(plan.date, [])
            for commit in plan.commits:
                bucket.append(_commit_payload(developer, plan.team, commit))
            for interruption in plan.interruptions:
                if interruption.source == "github":
                    bucket.append(_review_request_payload(developer, plan.team, interruption))
    return by_date


def extract_for_date(run_date: str, days: int = 14) -> list[dict]:
    return extract_recent(days=days).get(run_date, [])


def run(run_date: str | None = None, days: int = 14) -> str:
    """Airflow task entrypoint: extract and land raw JSON for one run_date."""
    from cognistream.extractors.base import utcnow_run_date

    run_date = run_date or utcnow_run_date()
    payload = extract_for_date(run_date, days=days)
    return write_raw_payload("github", run_date, payload)


if __name__ == "__main__":
    for date, payload in extract_recent().items():
        write_raw_payload("github", date, payload)
    print("GitHub mock extraction complete.")
