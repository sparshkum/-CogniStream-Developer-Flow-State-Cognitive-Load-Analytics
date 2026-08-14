# How to Run CogniStream

## Full stack (Docker — the real deployment)

Requires Docker Desktop (Airflow and ClickHouse are Linux-native and need
Docker or WSL2 to run on Windows).

```powershell
copy .env.example .env
docker-compose up -d --build
.\scripts\seed_demo_data.ps1
```

Then open:
- Dashboard: http://localhost:3000
- Backend API (Swagger docs): http://localhost:8000/docs
- Airflow UI: http://localhost:8080
- ClickHouse HTTP: http://localhost:8123

## Frontend only (no Docker needed)

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. Without a backend running, it will show a
"can't reach API" banner — that's expected. Point it at a running backend
with:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

## Backend only (needs a reachable ClickHouse instance)

```powershell
cd backend
.venv\Scripts\pip install -r requirements.txt
$env:CLICKHOUSE_HOST="localhost"
.venv\Scripts\uvicorn app.main:app --reload
```

Open http://localhost:8000/docs.

## Frontend + Backend together (two terminals)

Run these at the same time in two separate terminals so the dashboard has a
live API to call. Requires ClickHouse to be reachable (e.g. from
`docker-compose up -d clickhouse`) for the backend to start successfully.

**Terminal 1 — backend:**
```powershell
cd backend
.venv\Scripts\pip install -r requirements.txt
$env:CLICKHOUSE_HOST="localhost"
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```powershell
cd frontend
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

Then open http://localhost:5173 — it will call the backend on port 8000.

## Just the data pipeline (extract -> clean -> flow-state), no infra at all

```powershell
cd data-engineering
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python scripts\run_local_pipeline.py --days 14 --no-load
```

Add `--no-load` to skip loading into ClickHouse if one isn't running; drop
it once ClickHouse is reachable to load real data.

## Tests

```powershell
cd data-engineering; .venv\Scripts\pytest -q
cd backend; .venv\Scripts\pytest -q
cd frontend; npm run build
```
