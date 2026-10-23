# First product MVP runbook

This runbook proves the real PostgreSQL chain:

```text
seed -> schedule -> candidate (transport + warehouse) -> stored validation report
     -> commit -> current version/tasks
```

It is a local product candidate, **not** a signed Gate and not the full 109-task delivery.

## Prerequisites

- Python 3.12 and the workspace `.venv`
- PostgreSQL 17, isolated database
- `alembic upgrade head` applied
- optional: a real `DEEPSEEK_API_KEY` for the agent page

## 1. Database

```powershell
$env:DATABASE_URL='postgresql+psycopg://test:test@127.0.0.1:55432/dsh_test'
.\.venv\Scripts\alembic.exe upgrade head
```

## 2. Seed + end-to-end demo

```powershell
$env:DEMO_DATABASE_URL='postgresql+psycopg://test:test@127.0.0.1:55432/dsh_test'
.\.venv\Scripts\python.exe scripts/demo_product.py
```

Expected shape (IDs vary):

```json
{
  "schedule_id": "...",
  "candidate_id": "...",
  "candidate_valid": true,
  "version_no": 1,
  "version_id": "...",
  "current_tasks": 1,
  "current_hash": "..."
}
```

The demo imports the deterministic tiny scenario, creates a draft schedule, validates a
warehouse receive assignment through the server-side validator, commits the candidate atomically
and reads the current version back.

## 3. Tests

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://test:test@127.0.0.1:55432/dsh_test'
.\.venv\Scripts\pytest.exe tests -q
```

## 4. Frontend

```powershell
npm run build --workspace apps/frontend
npm run dev --workspace apps/frontend
```

Routes: `#/overview`, `#/schedules`, `#/transport`, `#/warehouse`, `#/simulation`,
`#/incidents`, `#/events`, `#/metrics`, `#/reschedule`, `#/agent`.

The login token is the development operator token configured on the backend
(`dev-operator-token` in the Docker compose example). Do not use it outside local development.

## 5. Docker stack

```powershell
docker compose config
docker compose build
docker compose up -d db backend worker frontend
docker compose run --rm seed
```

Open <http://localhost:8080>.

Known environment note: Docker Hub token exchange timed out over IPv6, but base images were pulled
from a registry mirror and tagged locally; backend/frontend/seed built successfully, the stack
started, and `/api/v1/health`, authenticated `/orders`, and a transport Job
(submit → worker → completed → result) all returned successfully.

The worker caps solver wall time at 5 seconds per job and backend/worker share a `results` volume
for immutable artifacts. The submitted `SolveBudgetDTO` is now pinned inside the job content, so a
1s/3s request budget is honored up to the 5s server cap.

Verified end-to-end in the Docker stack:

- seed import
- authenticated order query
- transport Job (1s budget) → completed → result with 1 route
- in-container demo → candidate valid, version 1, current task 1
- Nginx `/api/v1/schedules/{id}/versions/current` returns the committed version

## Known product gaps

- Most panels still accept raw JSON rather than form controls.
- Candidate creation accepts a pasted `TransportProblemDTO`; it is not yet generated directly from
  a transport Job artifact.
- Local rescheduling is a typed proposal, not a solved plan.
- Realtime events, full auth/user management, paired-seed experiment UI and release Gates remain
  out of MVP scope.
