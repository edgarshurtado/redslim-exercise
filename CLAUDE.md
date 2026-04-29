# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project overview

RedSlim Exercise — a small full-stack **Dataset Explorer MVP** for the retail-sales
datasets in `docs/data/` (`test_dataset.csv` and `unistar_dk/*.parquet`). See
`recruitment-exercise.md` for the original brief and `README.md` for setup.

The app exposes three exploration views over a normalized sales schema:
table exploration, manufacturer/brand dominance treemap, and a sales evolution
chart.

## Repo layout

```
backend/             Django project (redslim) + market_data app
  market_data/
    models.py            Brand / SubBrand / Product / Market / Data
    views.py             DRF views/viewsets (table, dominance, evolution)
    urls.py              /api/table/, /api/dominance/, /api/evolution/*
    management/commands/ load_csv, load_parquet
    tests/               pytest-django suites
  redslim/settings.py    Settings (env-driven)
  pytest.ini
frontend/            Vite + React 19 SPA
  src/
    App.tsx              Routes: /, /explore, /dominance, /evolution
    pages/               Landing, Explore, Dominance, Evolution (+ tests)
    components/Layout    Shared MUI layout
    api/client.ts        Axios client
docs/
  data/                  Source datasets (CSV + parquet)
  specs/00X_*.md         Per-feature specs the implementation followed
docker-compose.yml   Postgres 16 for local dev
```

## Stack

### Backend
- Django + Django REST Framework
- PostgreSQL (via Docker Compose)
- Pandas + pyarrow (data loaders)
- pytest / pytest-django

### Frontend
- React 19 + React Router 7
- Material UI v9 (`@mui/material`, `@emotion/react`)
- Tailwind CSS v3
- Recharts (charts)
- Axios
- Vite (dev/build), Jest + Testing Library (tests)

## Conventions

### Frontend
- **Avoid creating new components** — use MUI primitives whenever possible.
- **Avoid inline styles and custom CSS classes.** Use Tailwind utilities. The
  only allowed exception is MUI's `sx` prop.
- TypeScript throughout (`tsconfig.json`).

### Backend
- App code lives in `market_data/`. The Django project package is `redslim/`.
- Models use explicit `db_table` and `UniqueConstraint` names — keep that style
  if you add new models.
- Data loaders are idempotent (`get_or_create` / `ignore_conflicts`). Preserve
  this when extending them.

## Commands

### Database
```bash
docker compose up -d        # Postgres 16 on :5432 (db/user/pass: redslim)
```

### Backend (run from `backend/` with venv active)
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000

# Load sample data (idempotent)
python manage.py load_csv test_dataset.csv
python manage.py load_parquet unistar_dk

# Tests
pytest                      # whole suite
pytest market_data/tests/test_views.py        # single file
pytest -k evolution         # by keyword
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev                 # http://localhost:8080
npm run build
npm run lint
npm run typecheck           # tsc --noEmit
npm test                    # jest
npm test -- Evolution       # single test by name pattern
```

## Configuration

Backend reads from `backend/.env` (optional in dev — defaults match the
Compose Postgres). Keys: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`DATABASE_HOST`, `DATABASE_PORT`, `DJANGO_SECRET_KEY`, `DEBUG`,
`ALLOWED_HOSTS`. Frontend dev server runs on `:8080` and is allow-listed in
`CORS_ALLOWED_ORIGINS`.

## Data model (market_data)

`Brand → SubBrand → Product` hierarchy; `Market` is independent. `Data` is the
fact table joining `Market × Product` with `value`, `weighted_distribution`,
`date`, and `period_weeks`. Uniqueness on `(market, product, date)`.

## API surface

- `GET /api/table/` — paginated/filterable sales rows (DRF ViewSet)
- `GET /api/dominance/` — brand/manufacturer dominance aggregation (treemap)
- `GET /api/evolution/options/` — paginated selector options (infinite scroll)
- `GET /api/evolution/chart/` — time-series for selected products/markets

## Notes for changes

- New features generally have a matching spec under `docs/specs/`. When asked
  to implement something here, check whether a spec already exists.
- Tests live next to the code they cover (`market_data/tests/`,
  `frontend/src/**/*.test.tsx`). Add tests in the same place.
