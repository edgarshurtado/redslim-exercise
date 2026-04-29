# RedSlim Exercise — Dataset Explorer MVP

A small full-stack app for exploring the retail-sales datasets in `docs/data/`
(`test_dataset.csv` and `unistar_dk/*.parquet`). See
[`recruitment-exercise.md`](recruitment-exercise.md) for the brief.

## Stack

- **Backend:** Django + Django REST Framework, PostgreSQL, Pandas
- **Frontend:** React 19 + MUI + Tailwind, Vite, Recharts
- **Infra:** Docker Compose (Postgres only)

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+ and npm

## Dev setup

The three services (database, backend, frontend) run in separate terminals.

### 1. Database

From the repo root:

```bash
docker compose up -d
```

This starts Postgres 16 on `localhost:5432` with database `redslim-exercise`,
user `redslim`, password `redslim` (matches the defaults in
`backend/redslim/settings.py`).

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver 8000
```

The API is now on `http://localhost:8000`.

Settings read from `backend/.env` (see `redslim/settings.py` for the keys —
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_HOST`,
`DATABASE_PORT`, `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`). The defaults
work against the Docker Compose Postgres above, so a `.env` file is optional in
dev.

#### Load the sample data

Run these from `backend/` with the venv active:

```bash
# CSV dataset
python manage.py load_csv test_dataset.csv

# Parquet dataset (unistar_dk)
python manage.py load_parquet unistar_dk
```

Both commands are idempotent (`get_or_create` / `ignore_conflicts`), so it is
safe to re-run them.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is now on `http://localhost:8080` (port set in `vite.config.ts`, and
already allow-listed in the backend's `CORS_ALLOWED_ORIGINS`).

## Tests

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

## Repo layout

```
backend/        Django project (redslim) + market_data app
frontend/      Vite + React SPA
docs/data/     Source datasets (CSV + parquet)
docs/specs/    Per-feature specs the implementation followed
docker-compose.yml   Postgres for local dev
```
