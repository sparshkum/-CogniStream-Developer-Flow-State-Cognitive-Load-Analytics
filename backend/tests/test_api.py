"""API-shape smoke tests using a fake ClickHouseService, so the endpoint
contracts (routes, params, response schemas) can be verified without a real
ClickHouse server running.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.dependencies import get_ch_service
from app.main import app


class FakeClickHouseService:
    def list_teams(self):
        return ["Team A", "Team B"]

    def list_developers(self, team=None):
        return ["alice", "bob"] if team in (None, "Team A") else ["dinesh"]

    def summary(self, team, date_from, date_to):
        return {
            "developer_count": 3,
            "total_commits": 42,
            "total_hours_worked": 120.5,
            "avg_context_switch_tax_pct": 49.8,
            "total_interruptions": 60,
            "total_flow_blocks": 12,
            "avg_flow_block_minutes": 105.3,
        }

    def context_switch_tax_by_developer(self, team, date_from, date_to):
        return [
            {
                "developer": "alice",
                "team": "Team A",
                "flow_minutes": 300.0,
                "interrupted_minutes": 200.0,
                "total_coding_minutes": 500.0,
                "context_switch_tax_pct": 40.0,
            }
        ]

    def interruptions_by_source(self, team, date_from, date_to):
        return [{"source": "slack", "count": 30, "pct": 50.0}, {"source": "jira", "count": 20, "pct": 33.3}]

    def flow_blocks(self, team, date_from, date_to, min_duration, limit=200):
        now = datetime.now(timezone.utc)
        return [
            {
                "developer": "alice",
                "team": "Team A",
                "date": "2026-07-27",
                "block_start": now,
                "block_end": now,
                "duration_minutes": 95.0,
                "interrupted_by": None,
            }
        ]

    def flow_timeline(self, developer, date):
        now = datetime.now(timezone.utc)
        return [
            {
                "block_start": now,
                "block_end": now,
                "duration_minutes": 95.0,
                "is_flow_block": True,
                "interrupted_by": None,
            }
        ]


app.dependency_overrides[get_ch_service] = lambda: FakeClickHouseService()
client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_teams_and_developers():
    assert client.get("/api/teams").json() == ["Team A", "Team B"]
    assert client.get("/api/developers", params={"team": "Team A"}).json() == ["alice", "bob"]


def test_summary_shape():
    body = client.get("/api/summary").json()
    assert body["avg_context_switch_tax_pct"] == 49.8
    assert body["developer_count"] == 3


def test_context_switch_tax():
    body = client.get("/api/context-switch-tax", params={"team": "Team A"}).json()
    assert body[0]["developer"] == "alice"
    assert body[0]["context_switch_tax_pct"] == 40.0


def test_interruptions_by_source():
    body = client.get("/api/interruptions-by-source").json()
    assert body[0]["source"] == "slack"


def test_flow_blocks():
    body = client.get("/api/flow-blocks", params={"min_duration": 90}).json()
    assert body[0]["duration_minutes"] == 95.0


def test_flow_timeline_requires_developer():
    assert client.get("/api/flow-timeline").status_code == 422
    body = client.get("/api/flow-timeline", params={"developer": "alice", "date": "2026-07-27"}).json()
    assert body[0]["is_flow_block"] is True
