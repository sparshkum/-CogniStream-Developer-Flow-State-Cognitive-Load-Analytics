# Backfills 14 workdays of mock event data through the full CogniStream
# pipeline (extract -> clean -> flow-state -> load) into a running
# ClickHouse instance. Run this once after `docker-compose up -d` so the
# dashboard has history to show immediately, instead of waiting for the
# daily Airflow schedule to accumulate it one day at a time.
#
# Usage:
#   .\scripts\seed_demo_data.ps1                # assumes ClickHouse on localhost:8123
#   $env:CLICKHOUSE_HOST="localhost"; .\scripts\seed_demo_data.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dataEng = Join-Path $root "data-engineering"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment at .venv ..."
    python -m venv (Join-Path $root ".venv")
}

Write-Host "Installing data-engineering requirements ..."
& $venvPython -m pip install --quiet -r (Join-Path $dataEng "requirements.txt")

if (-not $env:CLICKHOUSE_HOST) { $env:CLICKHOUSE_HOST = "localhost" }
if (-not $env:CLICKHOUSE_PORT) { $env:CLICKHOUSE_PORT = "8123" }

Write-Host "Seeding 14 days of mock data into ClickHouse at $($env:CLICKHOUSE_HOST):$($env:CLICKHOUSE_PORT) ..."
Push-Location $dataEng
try {
    & $venvPython scripts/run_local_pipeline.py --days 14
} finally {
    Pop-Location
}
