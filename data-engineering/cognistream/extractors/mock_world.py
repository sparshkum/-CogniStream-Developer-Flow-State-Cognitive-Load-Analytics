"""Shared behavioral simulation that backs all four mock extractors.

In production, GitHub/Slack/Jira/ActivityWatch are four independent APIs that
happen to observe the same humans. To make the mock data support genuine
flow-state analysis (rather than data that is already pre-shaped into the
answer) we simulate one underlying "workday" per developer -- a timeline of
IDE heartbeats plus the interruption events that punctuate it -- and then
have each extractor emit only the slice of that timeline its real API would
expose, in that API's real response shape.

Team A is deliberately simulated with poor focus hygiene (frequent Slack /
Jira pings, short coding stretches) and Team B with good focus hygiene, so
the resulting dashboard reproduces the project's use case: "Team A loses
~40% of its cognitive flow state to context switching."
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from cognistream.config import PIPELINE

WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 17.5  # 17:30

# Per-team behavioral profile. `interrupt_rate` is the mean number of minutes
# of focused coding before an external interruption event fires;
# `deep_focus_bonus` widens the tail so some sessions run long enough to
# become genuine 90+ minute flow blocks.
TEAM_PROFILES = {
    "Team A": {"mean_focus_minutes": 85, "focus_stddev": 30, "interrupt_recovery_minutes": (4, 15)},
    "Team B": {"mean_focus_minutes": 112, "focus_stddev": 22, "interrupt_recovery_minutes": (2, 8)},
}
DEFAULT_PROFILE = {"mean_focus_minutes": 45, "focus_stddev": 20, "interrupt_recovery_minutes": (3, 10)}

INTERRUPTION_CHOICES = [
    ("slack", "message_received", 0.35),
    ("slack", "mention_received", 0.25),
    ("jira", "ticket_transitioned", 0.15),
    ("jira", "ticket_commented", 0.10),
    ("github", "pr_review_requested", 0.15),
]


@dataclass
class IdeHeartbeat:
    timestamp: datetime
    duration_seconds: float
    app: str
    window_title: str


@dataclass
class InterruptionEvent:
    timestamp: datetime
    source: str
    event_type: str
    metadata: dict


@dataclass
class CommitEvent:
    timestamp: datetime
    metadata: dict


@dataclass
class DayPlan:
    date: str
    developer: str
    team: str
    heartbeats: list[IdeHeartbeat] = field(default_factory=list)
    interruptions: list[InterruptionEvent] = field(default_factory=list)
    commits: list[CommitEvent] = field(default_factory=list)


def _seeded_rng(developer: str, date: str) -> random.Random:
    digest = hashlib.sha256(f"{developer}:{date}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _work_days(days: int, end_date: datetime | None = None) -> list[datetime]:
    end_date = end_date or datetime.now(timezone.utc)
    out = []
    d = end_date
    while len(out) < days:
        if d.weekday() < 5:  # Mon-Fri
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def build_day_plan(developer: str, team: str, day: datetime) -> DayPlan:
    date_str = day.strftime("%Y-%m-%d")
    rng = _seeded_rng(developer, date_str)
    profile = TEAM_PROFILES.get(team, DEFAULT_PROFILE)

    plan = DayPlan(date=date_str, developer=developer, team=team)

    cursor = day.replace(hour=WORKDAY_START_HOUR, minute=0, second=0, microsecond=0)
    end_of_day = day.replace(hour=int(WORKDAY_END_HOUR), minute=int((WORKDAY_END_HOUR % 1) * 60), second=0, microsecond=0)

    # Standup: short meeting near the start of the day, resets focus.
    cursor += timedelta(minutes=rng.randint(10, 20))

    while cursor < end_of_day:
        focus_minutes = max(4, rng.gauss(profile["mean_focus_minutes"], profile["focus_stddev"]))
        session_end = min(cursor + timedelta(minutes=focus_minutes), end_of_day)

        _emit_heartbeats(plan, rng, cursor, session_end)
        if rng.random() < 0.35:
            plan.commits.append(
                CommitEvent(
                    timestamp=session_end - timedelta(minutes=rng.uniform(0, min(5, focus_minutes))),
                    metadata={"lines_added": rng.randint(3, 220), "lines_removed": rng.randint(0, 90)},
                )
            )

        cursor = session_end
        if cursor >= end_of_day:
            break

        # Lunch break: one deterministic long idle gap, no interruption event.
        if 11.5 <= cursor.hour + cursor.minute / 60 <= 13.5 and not any(
            "lunch" in i.metadata.get("kind", "") for i in plan.interruptions
        ):
            lunch_minutes = rng.uniform(35, 55)
            plan.interruptions.append(
                InterruptionEvent(timestamp=cursor, source="calendar", event_type="lunch_break", metadata={"kind": "lunch"})
            )
            cursor += timedelta(minutes=lunch_minutes)
            continue

        # Otherwise: an external interruption fires and knocks the dev out of flow.
        source, event_type, meta = _sample_interruption(rng, developer)
        plan.interruptions.append(InterruptionEvent(timestamp=cursor, source=source, event_type=event_type, metadata=meta))

        recovery_low, recovery_high = profile["interrupt_recovery_minutes"]
        cursor += timedelta(minutes=rng.uniform(recovery_low, recovery_high))

    return plan


def _emit_heartbeats(plan: DayPlan, rng: random.Random, start: datetime, end: datetime) -> None:
    """Break one coding session into ~2-5 minute IDE heartbeats, the way a real
    ActivityWatch watcher polls the active window rather than logging one
    giant block. This is what gives flow_state.py real merging work to do.
    """
    apps = ["Code.exe"]
    files = ["dag_utils.py", "flow_state.py", "App.tsx", "events_schema.sql", "clean.py", "main.py"]
    cursor = start
    while cursor < end:
        beat_seconds = rng.uniform(90, 300)
        beat_end = min(cursor + timedelta(seconds=beat_seconds), end)
        plan.heartbeats.append(
            IdeHeartbeat(
                timestamp=cursor,
                duration_seconds=(beat_end - cursor).total_seconds(),
                app=rng.choice(apps),
                window_title=f"{rng.choice(files)} - CogniStream - Visual Studio Code",
            )
        )
        cursor = beat_end


def _sample_interruption(rng: random.Random, developer: str) -> tuple[str, str, dict]:
    r = rng.random()
    acc = 0.0
    for source, event_type, weight in INTERRUPTION_CHOICES:
        acc += weight
        if r <= acc:
            return source, event_type, _interruption_metadata(rng, source, event_type, developer)
    source, event_type, _ = INTERRUPTION_CHOICES[-1]
    return source, event_type, _interruption_metadata(rng, source, event_type, developer)


def _interruption_metadata(rng: random.Random, source: str, event_type: str, developer: str) -> dict:
    if source == "slack":
        return {
            "channel": rng.choice(["#eng-team", "#incidents", "#random", "#project-cognistream"]),
            "sender": rng.choice(["pm_jordan", "lead_sam", "qa_priya", "eng_manager"]),
            "kind": "mention" if event_type == "mention_received" else "message",
        }
    if source == "jira":
        return {
            "ticket": f"COGNI-{rng.randint(100, 999)}",
            "transition": rng.choice(["In Progress", "Blocked", "In Review"]) if event_type == "ticket_transitioned" else None,
            "kind": "jira",
        }
    if source == "github":
        return {
            "repo": "cognistream/platform",
            "pr_number": rng.randint(200, 480),
            "requested_by": rng.choice(["lead_sam", "eng_manager", "qa_priya"]),
            "kind": "review_request",
        }
    return {"kind": "other"}


def build_world(days: int | None = None) -> dict[str, list[DayPlan]]:
    """Return {developer: [DayPlan, ...]} for every developer in PIPELINE.teams."""
    days = days or 14
    work_days = _work_days(days)
    world: dict[str, list[DayPlan]] = {}
    for team, developers in PIPELINE.teams.items():
        for developer in developers:
            world[developer] = [build_day_plan(developer, team, day) for day in work_days]
    return world
