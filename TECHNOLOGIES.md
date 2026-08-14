# Technologies & Installation Guide

Everything used to build, run, and develop CogniStream, and exactly what to
install for each way of running it. See [README.md](README.md) for
architecture/use-case and [HOW_TO_RUN.md](HOW_TO_RUN.md) for run commands.

## Stack at a glance

| Layer | Technology | Version pinned in this repo |
|---|---|---|
| Orchestration | Apache Airflow | `2.10.4` (Python 3.11) — [data-engineering/airflow/Dockerfile](data-engineering/airflow/Dockerfile) |
| Orchestration DB | PostgreSQL | `16-alpine` (Airflow metadata store only) |
| OLAP database | ClickHouse | `24.8-alpine` |
| Data processing | Python + Polars | Python 3.11, `polars>=1.0` |
| ClickHouse client (Python) | clickhouse-connect | `>=0.7` |
| Backend API | FastAPI + Uvicorn | `fastapi>=0.115`, `uvicorn[standard]>=0.30` |
| Backend settings | pydantic-settings | `>=2.4` |
| Dashboard framework | React + Vite + TypeScript | React `18.3.1`, Vite `5.4.11`, TS `5.6.3` |
| Dashboard components | Tremor.js | `@tremor/react 3.18.7` |
| Styling | Tailwind CSS | `3.4.15` |
| Containerization | Docker + Docker Compose | any recent Docker Desktop |
| Testing (Python) | pytest | `>=8.0` (data-engineering and backend) |
| Testing (frontend) | TypeScript compiler / `tsc -b` | via `npm run build` |

## What to install

Pick based on what you're doing. All four are independent — you don't need
Docker to work on the Python pipeline or the frontend.

### 1. Full stack, real deployment (Airflow + ClickHouse for real)

Requires **Docker Desktop** (with WSL2 backend on Windows) — Airflow and
ClickHouse are Linux-native and this repo only ships Linux images for them.

- Install: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Nothing else to install locally — `docker-compose.yml` builds/pulls
  everything (Postgres, ClickHouse, Airflow webserver+scheduler, backend,
  frontend) inside containers.
- **Known gap on this machine:** no Docker Desktop and no WSL installed as of
  2026-07-28, so this path is unverified here — everything below was
  validated another way instead (see `project-cognistream` memory).

### 2. Data engineering only (extractors → Polars cleaning → flow-state), no infra

- Install: **Python 3.11+**
- `cd data-engineering && python -m venv .venv`
- `.venv\Scripts\pip install -r requirements.txt` → installs `polars`,
  `clickhouse-connect`, `pytest`
- Run without ClickHouse: `python scripts\run_local_pipeline.py --days 14 --no-load`
- Test: `.venv\Scripts\pytest -q`

### 3. Backend only (FastAPI), needs a reachable ClickHouse

- Install: **Python 3.11+**, plus either:
  - Docker Desktop just for the `clickhouse` service (`docker-compose up -d clickhouse`), or
  - a natively-installed ClickHouse server reachable at `CLICKHOUSE_HOST`
- `cd backend && python -m venv .venv`
- `.venv\Scripts\pip install -r requirements.txt` → installs `fastapi`,
  `uvicorn[standard]`, `clickhouse-connect`, `pydantic-settings`, `pytest`, `httpx`
- Test (no live ClickHouse needed — uses a fake dependency override):
  `.venv\Scripts\pytest -q`
- Run: `.venv\Scripts\uvicorn app.main:app --reload`

### 4. Frontend only (React + Tremor dashboard)

- Install: **Node.js 18+** (Vite 5 / `@vitejs/plugin-react` 4 requirement)
  and npm
- `cd frontend && npm install` → installs React, Tremor, Vite, TypeScript,
  Tailwind, and dev tooling from `package.json`
- Run: `npm run dev` (http://localhost:5173)
- Build/typecheck: `npm run build`

## Version requirements summary

| Tool | Minimum version | Why |
|---|---|---|
| Python | 3.11 | matches the Airflow image's Python and both `data-engineering`/`backend` venvs |
| Node.js | 18+ | required by Vite 5 / React 18 toolchain |
| npm | bundled with Node | installs `frontend/package.json` deps |
| Docker Desktop | recent, with WSL2 backend (Windows) | only path that can actually run Airflow 2.10.4 + ClickHouse 24.8 on this machine |
| git | any | version control (not yet initialized in this directory) |

## Notes specific to this machine

- No Docker Desktop or WSL is installed here, so Airflow and ClickHouse
  cannot run live locally — only Python (pipeline/backend) and Node
  (frontend) paths are runnable and have been verified (pytest + Playwright
  mocked-route checks). See `project-cognistream` memory for the full
  workaround rationale.
- If Docker Desktop gets installed later, re-check before assuming these
  workarounds still apply, then the full `docker-compose up -d --build`
  path becomes available end-to-end.
