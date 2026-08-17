"""Central configuration for the CogniStream data-engineering pipeline.

All settings are overridable via environment variables so the same code runs
unchanged locally, inside Airflow containers, and in CI.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class ClickHouseConfig:
    host: str = field(default_factory=lambda: _env("CLICKHOUSE_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(_env("CLICKHOUSE_PORT", "8123")))
    username: str = field(default_factory=lambda: _env("CLICKHOUSE_USER", "default"))
    password: str = field(default_factory=lambda: _env("CLICKHOUSE_PASSWORD", ""))
    database: str = field(default_factory=lambda: _env("CLICKHOUSE_DATABASE", "cognistream"))
    secure: bool = field(default_factory=lambda: _env("CLICKHOUSE_SECURE", "false").lower() == "true")


@dataclass(frozen=True)
class PipelineConfig:
    # Roster of developers being monitored. In a real deployment this would come
    # from an org directory sync; for the internship scope it is a static roster
    # shared by all mock extractors so events line up across sources.
    teams: dict = field(
        default_factory=lambda: {
            "Team A": ["alice", "bob", "carla"],
            "Team B": ["dinesh", "elena", "farid"],
        }
    )

    # Directory where raw extractor payloads (JSON) are dropped before cleaning.
    raw_data_dir: str = field(default_factory=lambda: _env("COGNISTREAM_RAW_DIR", "data/raw"))
    clean_data_dir: str = field(default_factory=lambda: _env("COGNISTREAM_CLEAN_DIR", "data/clean"))

    # A flow block is "uninterrupted" coding time: 90+ minutes with no
    # context-switch event, per the project spec.
    flow_block_min_minutes: float = field(
        default_factory=lambda: float(_env("COGNISTREAM_FLOW_MIN_MINUTES", "90"))
    )
    # Gaps in IDE activity shorter than this are treated as "still coding"
    # (e.g. reading docs, thinking) rather than a break in the flow block.
    idle_gap_tolerance_minutes: float = field(
        default_factory=lambda: float(_env("COGNISTREAM_IDLE_GAP_MINUTES", "10"))
    )

    def developers(self) -> list[str]:
        return [dev for devs in self.teams.values() for dev in devs]

    def team_for(self, developer: str) -> str:
        for team, devs in self.teams.items():
            if developer in devs:
                return team
        return "Unassigned"


CLICKHOUSE = ClickHouseConfig()
PIPELINE = PipelineConfig()
