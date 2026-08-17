"""CogniStream orchestration DAG.

Scheduled daily. Pulls yesterday's event logs from the four developer APIs
(GitHub, Slack, Jira, ActivityWatch/VSCode), cleans and merges them with
Polars, computes Uninterrupted Flow Blocks + the Context-Switching Tax, and
loads everything into ClickHouse for the dashboard to read.

Every task here is a thin wrapper around `cognistream.pipeline` -- the DAG
file itself contains no business logic, so the pipeline can be (and is)
unit-tested without an Airflow install. See data-engineering/tests/.
"""
from __future__ import annotations

import datetime

from airflow.decorators import dag, task

default_args = {
    "owner": "cognistream",
    "retries": 2,
    "retry_delay": datetime.timedelta(minutes=5),
}


@dag(
    dag_id="cognistream_pipeline",
    description="Extract developer event logs -> clean -> compute flow state -> load into ClickHouse",
    schedule="@daily",
    start_date=datetime.datetime(2026, 7, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["cognistream", "flow-state"],
)
def cognistream_pipeline():
    @task
    def extract_github(ds: str | None = None) -> None:
        from cognistream.extractors import github_extractor

        github_extractor.run(run_date=ds)

    @task
    def extract_slack(ds: str | None = None) -> None:
        from cognistream.extractors import slack_extractor

        slack_extractor.run(run_date=ds)

    @task
    def extract_jira(ds: str | None = None) -> None:
        from cognistream.extractors import jira_extractor

        jira_extractor.run(run_date=ds)

    @task
    def extract_activitywatch(ds: str | None = None) -> None:
        from cognistream.extractors import activitywatch_extractor

        activitywatch_extractor.run(run_date=ds)

    @task
    def clean(ds: str | None = None) -> str:
        from cognistream import pipeline

        events = pipeline.clean_day(ds)
        return f"cleaned {events.height} events for {ds}"

    @task
    def compute_flow_state(ds: str | None = None) -> str:
        from cognistream import pipeline

        blocks, daily = pipeline.compute_flow_state(ds)
        return f"{blocks.height} flow blocks across {daily.height} developer-days for {ds}"

    @task
    def load_clickhouse(ds: str | None = None) -> dict:
        from cognistream import pipeline

        return pipeline.load_to_clickhouse(ds)

    extractions = [extract_github(), extract_slack(), extract_jira(), extract_activitywatch()]
    cleaned = clean()
    flow_state_result = compute_flow_state()
    loaded = load_clickhouse()

    extractions >> cleaned >> flow_state_result >> loaded


cognistream_pipeline()
