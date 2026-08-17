"""Canonical event schema shared by every extractor, the Polars cleaning step,
and the ClickHouse `events` table. Each raw API payload (GitHub, Slack, Jira,
ActivityWatch) is normalized into this shape before it ever touches storage.
"""
from __future__ import annotations

from typing import TypedDict


class Source:
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    ACTIVITYWATCH = "activitywatch"


class EventType:
    # GitHub
    COMMIT = "commit"
    PR_OPENED = "pr_opened"
    PR_REVIEW_REQUESTED = "pr_review_requested"
    # Slack
    MESSAGE_RECEIVED = "message_received"
    MENTION_RECEIVED = "mention_received"
    # Jira
    TICKET_TRANSITIONED = "ticket_transitioned"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_COMMENTED = "ticket_commented"
    # ActivityWatch
    IDE_ACTIVE = "ide_active"


# Event types that represent the developer *choosing* to act (coding output,
# not an externally-triggered context switch). Everything else that targets
# the developer while a coding session is in progress is a candidate
# "interruption trigger" for the flow-state algorithm.
NON_INTERRUPTING_EVENT_TYPES = {EventType.COMMIT, EventType.IDE_ACTIVE}


class CanonicalEvent(TypedDict):
    event_id: str
    developer: str
    team: str
    source: str
    event_type: str
    event_time: str  # ISO-8601 UTC, e.g. "2026-07-14T09:32:11.000000Z"
    duration_seconds: float  # 0 for point-in-time events (messages, commits, ...)
    metadata: str  # JSON-encoded string with source-specific detail
