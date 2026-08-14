# CogniStream

**Developer Flow-State & Cognitive Load Analytics**

## Problem statement

Engineering productivity is usually measured with flawed, output-only metrics
like "lines of code written" or "tickets closed." Those numbers overlook the
*friction* of the development process itself, and fail to identify what
actually blocks focused, deep work.

## Use case

An Engineering Manager opens the CogniStream dashboard. Instead of seeing how
many commits Team A pushed or how many Jira tickets they closed, they see a
**Context-Switching Tax**: the dashboard proves that Team A loses roughly half
of their potential cognitive flow state to constant task switching between
Jira, Slack, and their IDE -- while Team B, with better focus hygiene, loses
much less. That's the lever the manager can actually pull: adjust
notification policies, protect focus blocks, and improve the day-to-day
developer experience, instead of chasing vanity metrics.

## Architecture

```
GitHub API  ─┐
Slack API   ─┤                                    ┌──────────────┐
Jira API    ─┼──▶ Airflow DAG (daily) ──▶ Polars ──▶│  ClickHouse  │
ActivityWatch┘     extract raw JSON      clean +    │  events /    │
 (VSCode)          per source            compute     flow_blocks /  │
                                          flow state  daily_metrics │
                                                      └──────┬───────┘
                                                             │ SQL (aggregated)
                                                      ┌──────▼───────┐
                                                      │   FastAPI     │
                                                      └──────┬───────┘
                                                             │ JSON
                                                      ┌──────▼───────┐
                                                      │ React + Tremor│
                                                      │   Dashboard   │
                                                      └───────────────┘
```

Every source in this project (GitHub, Slack, Jira, ActivityWatch) is a mock
extractor that reproduces the real API's response shape, so the cleaning and
flow-state logic downstream does genuine normalization/analytics work rather
than reading pre-shaped data. See "About the mock data" below.

## Key modules (only these technologies are used)

| Module | Technology |
|---|---|
| Orchestration | Apache Airflow (scheduled daily DAG) |
| OLAP database | ClickHouse |
| Data processing | Python + Polars |
| Backend API | FastAPI |
| Dashboard | React + Tremor.js |

## Repository layout

```
data-engineering/
  cognistream/
    extractors/      Mock GitHub / Slack / Jira / ActivityWatch extractors + shared world simulation
    processing/       clean.py (Polars normalization), flow_state.py (flow blocks + context-switch tax)
    storage/           ClickHouse client + loader
    pipeline.py        Single source of truth: extract -> clean -> flow-state -> load
    config.py          Team/developer roster, thresholds, ClickHouse connection settings
  airflow/dags/        cognistream_pipeline_dag.py (thin wrapper over cognistream.pipeline)
  clickhouse/init/     SQL schema: events, flow_blocks, daily_metrics
  scripts/             run_local_pipeline.py (no-Airflow dev/demo runner)
  tests/                pytest suite for extractors, cleaning, flow-state logic
backend/
  app/                 FastAPI app: routers, ClickHouse SQL service, Pydantic schemas
  tests/                API-shape tests (fake ClickHouse service, no infra required)
frontend/
  src/                 React + Tremor.js dashboard (Vite + TypeScript + Tailwind)
docker-compose.yml      Airflow (webserver+scheduler+Postgres) + ClickHouse + backend + frontend
scripts/                 seed_demo_data.ps1 / .sh -- backfill 14 days of demo data
```

## Quick start (Docker)

Requires Docker Desktop (Airflow and ClickHouse are Linux-native services and
don't run outside containers on Windows without Docker/WSL).

```powershell
copy .env.example .env
docker-compose up -d --build
```

This starts:

| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 (login: `admin` / `admin` by default, see `.env`) |
| ClickHouse HTTP | http://localhost:8123 |
| Backend API (Swagger docs) | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |

The Airflow DAG `cognistream_pipeline` is scheduled `@daily` and paused by
default -- unpause it in the Airflow UI to let it run, or backfill history
immediately so the dashboard isn't empty on first launch:

```powershell
.\scripts\seed_demo_data.ps1
```

(`./scripts/seed_demo_data.sh` on macOS/Linux.) This runs the exact same
`cognistream.pipeline` code the DAG uses, just invoked directly against the
ClickHouse port Docker Compose publishes to `localhost`, backfilling the
last 14 workdays so the dashboard has a real trend to show.

## Local development (no Docker)

Airflow and ClickHouse don't run natively on Windows, but everything else
does, and the whole pipeline is fully unit-tested without either:

```powershell
# Data engineering (extract -> clean -> flow-state), no ClickHouse required
cd data-engineering
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pytest -q
.venv\Scripts\python scripts\run_local_pipeline.py --days 14 --no-load

# Backend API (point at a ClickHouse instance, e.g. from docker-compose)
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pytest -q
$env:CLICKHOUSE_HOST="localhost"
.venv\Scripts\uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Week-by-week build (as delivered)

- **Week 1 -- Data Engineering + UI Scaffolding**: mock extractors for
  GitHub/Slack/Jira/ActivityWatch (`cognistream/extractors/`), an Airflow DAG
  scheduling them daily, and a Vite + React + Tremor.js app shell.
- **Week 2 -- Data Modeling + Base Metrics**: ClickHouse `events` table
  (`clickhouse/init/002_events_table.sql`), Polars cleaning
  (`processing/clean.py`) normalizing all four raw API shapes into it, and
  dashboard KPI cards for raw metrics (commits, hours worked).
- **Mid-project audit**: `tests/test_extractors.py` and
  `tests/test_clean.py` prove the DAG's extract+clean steps run correctly
  end to end; `clickhouse/init/*.sql` shows the MergeTree partitioning/
  ordering chosen for time-series queries.
- **Week 3 -- Flow-State Logic + Friction UI**: `processing/flow_state.py`
  merges ActivityWatch heartbeats into coding sessions and splits them at
  every Slack/Jira/GitHub interruption event to find genuine 90+ minute
  "Uninterrupted Flow Blocks"; the dashboard's Context-Switching Tax chart
  and Flow Timeline visualize exactly when and why flow breaks.
- **Week 4 -- API Layer + Polish**: FastAPI (`backend/`) serves aggregated
  ClickHouse queries to the dashboard; Tremor cards/charts/table polished
  for a manager-facing view.
- **Final -- Full pipeline + unified dashboard**: `docker-compose.yml` wires
  Airflow, ClickHouse, the API, and the dashboard into one stack;
  `cognistream.pipeline` is the single orchestration path both the DAG and
  the local dev runner use.

## About the mock data

There's no real GitHub/Slack/Jira/ActivityWatch account wired up -- per the
project brief, each extractor generates data shaped exactly like the real
API's response (GitHub commit/review-request payloads, Slack
`conversations.history` messages, Jira issue-changelog webhooks, and
ActivityWatch's `/buckets/{id}/events` heartbeats). All four are generated
from one shared, seeded simulation (`extractors/mock_world.py`) so a Slack
ping, the IDE going idle, and a Jira ticket transition for the same
developer on the same day are mutually consistent, the way they would be in
production. Team A is simulated with poor focus hygiene (frequent pings,
short coding stretches) and Team B with good focus hygiene, so the dashboard
reproduces the project's use case: Team A shows a materially higher
Context-Switching Tax than Team B.

## Testing

```powershell
cd data-engineering; .venv\Scripts\pytest -q   # extractors, cleaning, flow-state logic
cd backend; .venv\Scripts\pytest -q             # API routes/schemas against a fake ClickHouse service
cd frontend; npm run build                      # type-check + production bundle
```
