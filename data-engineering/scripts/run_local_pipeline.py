"""Run the full CogniStream pipeline (extract -> clean -> flow-state -> load)
for a range of days without Airflow. This is the everyday dev-loop entrypoint
on a machine without Docker/Airflow installed (Airflow only runs on
Linux/WSL/Docker), and it's also how the Docker Compose stack gets seeded
with enough history for the dashboard to have something to show on first run.

Usage (from data-engineering/, with the venv active):
    python scripts/run_local_pipeline.py --days 14
    python scripts/run_local_pipeline.py --days 14 --no-load   # skip ClickHouse
    python scripts/run_local_pipeline.py --date 2026-07-27     # a single day
"""
from __future__ import annotations

import argparse
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cognistream import pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cognistream.run_local_pipeline")


def _last_n_workdays(n: int) -> list[str]:
    days: list[str] = []
    cursor = datetime.datetime.now(datetime.timezone.utc)
    while len(days) < n:
        if cursor.weekday() < 5:
            days.append(cursor.strftime("%Y-%m-%d"))
        cursor -= datetime.timedelta(days=1)
    return list(reversed(days))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=14, help="How many trailing workdays to process (default: 14).")
    parser.add_argument("--date", type=str, default=None, help="Process a single YYYY-MM-DD date instead of a range.")
    parser.add_argument("--no-load", action="store_true", help="Skip loading into ClickHouse (extract+clean+flow-state only).")
    args = parser.parse_args()

    run_dates = [args.date] if args.date else _last_n_workdays(args.days)
    load = not args.no_load

    if load:
        logger.info("Will load into ClickHouse at %s -- pass --no-load to skip this.", "http://localhost:8123 (or CLICKHOUSE_HOST)")

    results = []
    for run_date in run_dates:
        logger.info("=== Running pipeline for %s ===", run_date)
        try:
            summary = pipeline.run_pipeline_for_date(run_date, days_context=max(args.days, 14), load=load)
            results.append(summary)
        except Exception:
            logger.exception("Pipeline failed for %s", run_date)
            raise

    total_events = sum(r["events"] for r in results)
    total_blocks = sum(r["flow_blocks"] for r in results)
    logger.info("Done. %d day(s) processed, %d events cleaned, %d flow blocks computed.", len(results), total_events, total_blocks)


if __name__ == "__main__":
    main()
