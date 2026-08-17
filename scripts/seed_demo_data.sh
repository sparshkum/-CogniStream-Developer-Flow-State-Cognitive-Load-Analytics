#!/usr/bin/env bash
# Backfills 14 workdays of mock event data through the full CogniStream
# pipeline (extract -> clean -> flow-state -> load) into a running
# ClickHouse instance. Run this once after `docker-compose up -d` so the
# dashboard has history to show immediately, instead of waiting for the
# daily Airflow schedule to accumulate it one day at a time.
#
# Usage:
#   ./scripts/seed_demo_data.sh                  # assumes ClickHouse on localhost:8123
#   CLICKHOUSE_HOST=localhost ./scripts/seed_demo_data.sh
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_eng="$root/data-engineering"
venv_python="$root/.venv/bin/python"

if [ ! -x "$venv_python" ]; then
    echo "Creating virtual environment at .venv ..."
    python3 -m venv "$root/.venv"
fi

echo "Installing data-engineering requirements ..."
"$venv_python" -m pip install --quiet -r "$data_eng/requirements.txt"

export CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
export CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-8123}"

echo "Seeding 14 days of mock data into ClickHouse at ${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT} ..."
cd "$data_eng"
"$venv_python" scripts/run_local_pipeline.py --days 14
