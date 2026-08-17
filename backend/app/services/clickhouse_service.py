"""All ClickHouse SQL for the dashboard lives here. Every query is
parameterized through clickhouse-connect's `parameters=` binding -- team,
date-range, and developer filters all come from user-controlled query
strings, so nothing is ever string-formatted into the SQL text.
"""
from __future__ import annotations

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.config import settings

EVENTS = "cognistream.events"
FLOW_BLOCKS = "cognistream.flow_blocks"
DAILY_METRICS = "cognistream.daily_metrics"

# Event types that represent the developer's own output rather than an
# externally triggered context switch. Mirrors
# cognistream.schemas.NON_INTERRUPTING_EVENT_TYPES in the data-engineering
# package -- duplicated here rather than imported so the API container has
# no dependency on the Airflow/data-engineering codebase.
NON_INTERRUPTING_EVENT_TYPES = ("commit", "ide_active")


class ClickHouseService:
    def __init__(self, client: Client):
        self.client = client

    @classmethod
    def connect(cls) -> "ClickHouseService":
        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            secure=settings.clickhouse_secure,
        )
        return cls(client)

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _team_filter_clause(team: str | None) -> str:
        return "" if not team else "AND team = %(team)s"

    def list_teams(self) -> list[str]:
        result = self.client.query(f"SELECT DISTINCT team FROM {EVENTS} ORDER BY team")
        return [row[0] for row in result.result_rows]

    def list_developers(self, team: str | None = None) -> list[str]:
        sql = f"SELECT DISTINCT developer FROM {EVENTS} WHERE 1=1 {self._team_filter_clause(team)} ORDER BY developer"
        result = self.client.query(sql, parameters={"team": team or ""})
        return [row[0] for row in result.result_rows]

    def summary(self, team: str | None, date_from: str, date_to: str) -> dict:
        team_clause = self._team_filter_clause(team)
        params = {"team": team or "", "date_from": date_from, "date_to": date_to}

        daily_sql = f"""
            SELECT
                count(DISTINCT developer) AS developer_count,
                sum(total_commits) AS total_commits,
                round(sum(total_coding_minutes) / 60.0, 1) AS total_hours_worked,
                round(avg(context_switch_tax_pct), 1) AS avg_context_switch_tax_pct,
                sum(total_interruption_events) AS total_interruptions,
                sum(num_flow_blocks) AS total_flow_blocks
            FROM {DAILY_METRICS}
            WHERE date BETWEEN %(date_from)s AND %(date_to)s {team_clause}
        """
        daily_row = self.client.query(daily_sql, parameters=params).first_row

        flow_sql = f"""
            SELECT round(avg(duration_minutes), 1) AS avg_flow_block_minutes
            FROM {FLOW_BLOCKS}
            WHERE is_flow_block = 1 AND date BETWEEN %(date_from)s AND %(date_to)s {team_clause}
        """
        flow_row = self.client.query(flow_sql, parameters=params).first_row

        keys = ["developer_count", "total_commits", "total_hours_worked", "avg_context_switch_tax_pct", "total_interruptions", "total_flow_blocks"]
        summary = dict(zip(keys, daily_row)) if daily_row else {k: 0 for k in keys}
        summary["avg_flow_block_minutes"] = flow_row[0] if flow_row and flow_row[0] is not None else 0.0
        return summary

    def context_switch_tax_by_developer(self, team: str | None, date_from: str, date_to: str) -> list[dict]:
        sql = f"""
            SELECT
                developer,
                team,
                round(sum(flow_minutes), 1) AS flow_minutes,
                round(sum(interrupted_minutes), 1) AS interrupted_minutes,
                round(sum(total_coding_minutes), 1) AS total_coding_minutes,
                round(sumIf(interrupted_minutes, total_coding_minutes > 0) / nullIf(sum(total_coding_minutes), 0) * 100, 1) AS context_switch_tax_pct
            FROM {DAILY_METRICS}
            WHERE date BETWEEN %(date_from)s AND %(date_to)s {self._team_filter_clause(team)}
            GROUP BY developer, team
            ORDER BY context_switch_tax_pct DESC
        """
        result = self.client.query(sql, parameters={"team": team or "", "date_from": date_from, "date_to": date_to})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def interruptions_by_source(self, team: str | None, date_from: str, date_to: str) -> list[dict]:
        placeholders = ", ".join(f"'{t}'" for t in NON_INTERRUPTING_EVENT_TYPES)
        sql = f"""
            SELECT source, count(*) AS count
            FROM {EVENTS}
            WHERE event_type NOT IN ({placeholders})
              AND event_date BETWEEN %(date_from)s AND %(date_to)s
              {self._team_filter_clause(team)}
            GROUP BY source
            ORDER BY count DESC
        """
        result = self.client.query(sql, parameters={"team": team or "", "date_from": date_from, "date_to": date_to})
        rows = [dict(zip(result.column_names, row)) for row in result.result_rows]
        total = sum(row["count"] for row in rows) or 1
        for row in rows:
            row["pct"] = round(row["count"] / total * 100, 1)
        return rows

    def flow_blocks(self, team: str | None, date_from: str, date_to: str, min_duration: float, limit: int = 200) -> list[dict]:
        sql = f"""
            SELECT developer, team, date, block_start, block_end, duration_minutes, interrupted_by
            FROM {FLOW_BLOCKS}
            WHERE is_flow_block = 1
              AND date BETWEEN %(date_from)s AND %(date_to)s
              AND duration_minutes >= %(min_duration)s
              {self._team_filter_clause(team)}
            ORDER BY duration_minutes DESC
            LIMIT %(limit)s
        """
        result = self.client.query(
            sql, parameters={"team": team or "", "date_from": date_from, "date_to": date_to, "min_duration": min_duration, "limit": limit}
        )
        return [dict(zip(result.column_names, row)) for row in result.result_rows]

    def flow_timeline(self, developer: str, date: str) -> list[dict]:
        sql = f"""
            SELECT block_start, block_end, duration_minutes, is_flow_block, interrupted_by
            FROM {FLOW_BLOCKS}
            WHERE developer = %(developer)s AND date = %(date)s
            ORDER BY block_start
        """
        result = self.client.query(sql, parameters={"developer": developer, "date": date})
        return [dict(zip(result.column_names, row)) for row in result.result_rows]
