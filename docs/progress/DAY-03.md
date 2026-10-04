# Day 03 Checkpoint

## Objective
Integrate PostgreSQL as the primary application database without breaking existing functionality or the test suite.

## Initial State
At the start of Day 3, the repository had:
- Day 2 commit e6f956f: structured JSON logging, request ID middleware, centralized Pydantic v2 configuration, exception handling
- All 9 backend tests passing
- SQLite (file-based) as the only database, created via `create_engine(settings.database_url, connect_args={"check_same_thread": False})`
- No migration tooling (tables created via `Base.metadata.create_all` on startup)
- Docker Compose with backend + frontend only; no database service
- Health endpoint hardcoding `database_connected=True`

## Changes Made

### Database Layer (`backend/app/database.py`)
- Added `_create_engine_from_url()`: builds the SQLAlchemy engine with dialect-appropriate settings.
  - SQLite: `check_same_thread=False` (unchanged behavior).
  - PostgreSQL and other server databases: connection pooling with `pool_size`, `max_overflow`, `pool_timeout`, `pool_pre_ping=True`, and `pool_recycle`.
- Added `check_db_connection()`: executes `SELECT 1` and returns a boolean; never raises (used by the health endpoint).
- `init_db()` now retries up to 5 times with a 2s delay so the app survives PostgreSQL still starting up (e.g. first `docker compose up`), and raises a clear error if the database never becomes reachable.
- Models (`TransactionDB`, `AlertDB`) are unchanged -- the same schema works on both SQLite and PostgreSQL.

### Configuration (`backend/app/config.py`)
- `database_url` remains the single source of truth, overridable via the `DATABASE_URL` environment variable. Default stays SQLite for local development without Docker.
- New pool settings (used only for server databases): `db_pool_size` (5), `db_max_overflow` (10), `db_pool_timeout` (30s), `db_pool_recycle_seconds` (1800).

### PostgreSQL Driver & Migrations
- Added `psycopg2-binary==2.9.10` (PostgreSQL driver) and `alembic==1.14.0` (migrations) to `backend/requirements.txt`.
- Added Alembic scaffolding under `backend/alembic/` plus `backend/alembic.ini`:
  - `alembic/env.py` reads the URL from centralized settings -- no credentials in `alembic.ini`.
  - `alembic/versions/0001_initial_schema.py` -- initial migration creating `transactions` and `alerts` with their indexes, matching the SQLAlchemy models.
- Apply migrations with: `cd backend && alembic upgrade head`
  (The app still calls `init_db()` / `create_all` on startup for convenience; Alembic is the strategy for future schema evolution.)

### Health Endpoint (`backend/app/main.py`)
- `/health` now reports a real `database_connected` value from `check_db_connection()` and returns `status="degraded"` if the database is unreachable (previously hardcoded `True`).

### Docker Compose (`docker-compose.yml`)
- New `db` service: `postgres:16-alpine` with:
  - Credentials from environment (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) with development defaults -- no hardcoded production secrets.
  - Persistent volume `postgres-data`.
  - Health check via `pg_isready` (5s interval, 10 retries).
  - `restart: unless-stopped`.
- `backend` now:
  - Waits for `db: service_healthy` before starting.
  - Uses `DATABASE_URL=postgresql+psycopg2://...@db:5432/...` composed from the same env vars.
  - `restart: unless-stopped`.
- `.env.example` added at the repo root documenting every variable.

### Tests (`backend/tests/test_database.py` -- new)
- SQLite engine uses `check_same_thread=False`; test suite isolation unchanged (in-memory SQLite, StaticPool).
- PostgreSQL engine is built with the configured pool size, overflow, and pre-ping (configuration verified without requiring a live server).
- `check_db_connection()` returns `True` on a working database and `False` (no exception) on a broken one.
- `init_db()` creates both tables.
- Sessions close cleanly.

Existing tests continue to run against in-memory SQLite -- the suite does not require a running PostgreSQL server. (`test_api.py` later gained alert-lifecycle and drift tests during the Day 3 final review; `test_ml.py` remains unchanged.)

## Commands

```bash
# Install new dependencies
pip install -r backend/requirements.txt

# Run tests (SQLite in-memory, no PostgreSQL needed)
cd backend && python -m pytest tests/ -v

# Start the full stack with PostgreSQL
cp .env.example .env   # edit credentials
docker compose up --build

# Apply / manage migrations
cd backend
alembic upgrade head            # apply
alembic downgrade base          # roll back
alembic revision --autogenerate -m "message"   # new migration after model changes
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./data/fraud.db` | Full SQLAlchemy URL |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `fraud` / `changeme` / `fraud_detection` | Docker Compose PostgreSQL credentials |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT` / `DB_POOL_RECYCLE_SECONDS` | `5` / `10` / `30` / `1800` | Connection pooling (server DBs only) |

## Tests Executed
- Command: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -v`
  (run from the `backend` directory using the project virtual environment;
  running from the repository root causes import resolution issues due to the
  package layout).
- Initial run after the PostgreSQL integration: 15 passed, 0 failed
  (9 pre-existing tests + 6 new database tests from `tests/test_database.py`).
- The final review then added 4 more tests (alert acknowledge/resolve lifecycle:
  200, 400-on-repeat, 404-on-unknown; plus drift-math verification) covering bugs
  fixed in `backend/app/api/routes.py`.
- Final run: **19 passed, 0 failed, in 7.03 seconds.**

## Live PostgreSQL Verification (manual, 2026-10-04)
- PostgreSQL 16 Docker container healthy (`pg_isready` healthcheck passing).
- `alembic upgrade head` applied migration `0001_initial_schema` successfully.
- `GET /health` -> `healthy`, `model_loaded=true`, `database_connected=true`.
- Submitted `txn_day3_pg_verify_001` via `POST /api/v1/score`; row confirmed in
  PostgreSQL via direct SQL query; retrieved via `GET /api/v1/transactions`.
- `GET /api/v1/metrics` reported the persisted transaction.

## Drift Investigation (drift_score=1.9364 after one transaction)
Expected behavior, not a bug. `_compute_drift()` computes a z-score:
`|mean(window scores) - reference_mean| / reference_std`, compared against
`drift_threshold=0.15`. The training baseline is `mean_score=0.0885`,
`std_score=0.2789` (ml/artifacts/metadata.json). A single transaction scoring
~0.6286 yields `|0.6286 - 0.0885| / 0.2789 ~= 1.9364 > 0.15` -> `drift_detected=true`.
The math is correct per the design; with very few transactions the windowed mean is
dominated by individual scores, so any score above ~0.13 flags drift. The threshold
is configurable via `DRIFT_THRESHOLD`. A test
(`test_drift_computation_matches_baseline`) locks in the intended math.

## Day 3 Final Review Fixes
- `backend/app/api/routes.py`: added missing `HTTPException`, `datetime`, and
  `timezone` imports (acknowledge/resolve alert endpoints would have raised
  `NameError`), and removed a duplicate `monitoring` import. New tests cover the
  acknowledge/resolve lifecycle (200, 400 on repeat, 404 on unknown).
- `.env.example`: `ALLOWED_ORIGINS` documented as a JSON array
  (`["http://localhost:5173"]`) to match pydantic-settings list parsing and the
  docker-compose value.

## Preserved Functionality
Single & batch scoring, high-risk scoring, transaction listing, metrics, alerts, health endpoint, and WebSocket streaming all verified by the unchanged test suite.

## Known Issues / Notes
- Docker-based PostgreSQL end-to-end verified live (see above); automated tests intentionally remain SQLite-based and do not require a database server.
- `init_db()` (create_all) still runs at startup; Alembic owns schema evolution going forward.
- WebSocket streaming module (`backend/app/api/websocket.py`) had a latent Day 2 bug (missing `import uuid`); fixed during Day 3 implementation.

## Migration Consistency Review
`backend/alembic/versions/0001_initial_schema.py` was compared column-by-column
against the SQLAlchemy models in `backend/app/database.py`:
- `transactions`: id (Integer, PK, autoincrement), transaction_id (String(64),
  NOT NULL, unique index `ix_transactions_transaction_id`), amount (Float),
  merchant_category (String(32)), fraud_score (Float), risk_level (String(16)),
  is_fraud (Boolean), latency_ms (Float), model_version (String(32)),
  features_json (Text) -- all NOT NULL, matching; scored_at (DateTime, nullable,
  indexed via `ix_transactions_scored_at`).
- `alerts`: id (Integer, PK, autoincrement), alert_id (String(64), NOT NULL,
  unique index `ix_alerts_alert_id`), alert_type (String(32)), severity
  (String(16)), message (Text), value (Float), threshold (Float) -- all NOT NULL,
  matching; created_at / acknowledged_at / resolved_at (DateTime, nullable) and
  resolved (Boolean, nullable).
- Defaults (`scored_at`, `created_at`, `resolved=False`) are Python-side column
  defaults in the models; the migration intentionally has no server defaults,
  so behavior is identical on SQLite and PostgreSQL.
- Result: migration, models, and the applied PostgreSQL schema are consistent.
  No changes made; the applied migration was left untouched (no downgrade, no
  reset, no volume deletion).

## Day 3 Status
COMPLETE and VERIFIED - PostgreSQL integrated as the primary database with
pooling, retries, real health checks, Alembic migrations, and a Docker Compose
PostgreSQL service. Full backend suite: 19 passed, 0 failed (7.03s). Live
PostgreSQL persistence verified manually against the running Docker stack.
Migration consistency between models, migration, and applied schema confirmed.
