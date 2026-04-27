# Spec 001 — Project Scaffolding

Set up a fullstack project with two local development servers (frontend, backend) and one Docker container (PostgreSQL). Each stack lives in its own folder. The goal is a minimal but fully wired environment where each layer is reachable and communicates correctly.

---

## Project Structure

```
redslim-exercise/
├── frontend/        # React app
├── backend/         # Django app
└── docker-compose.yml
```

---

## Services

### 1. Frontend (local)
- **Folder:** `frontend/`
- **Stack:** React, React Material UI, Vite, Tailwind CSS, Axios, Jest
- **Port:** `8080`
- **Start command:** `npm run dev`

### 2. Backend (local)
- **Folder:** `backend/`
- **Stack:** Django, Django REST Framework, Pandas, Pytest
- **Port:** `8000`
- **Start command:** `python manage.py runserver`

### 3. Database (Docker)
- **Image:** PostgreSQL (latest stable)
- **Port:** `5432`
- **Database:** `redslim-exercise`
- **User:** `redslim`
- **Password:** `redslim`
- **Start command:** `docker compose up`

---

## Configuration

**`docker-compose.yml`** exposes the PostgreSQL container on `localhost:5432`.

**`backend/`** connects to the DB via environment variables (`.env` or shell):
```
POSTGRES_DB=redslim-exercise
POSTGRES_USER=redslim
POSTGRES_PASSWORD=redslim
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

**`frontend/`** points to the backend via a Vite env variable:
```
API_BASE_URL=http://localhost:8000
```

---

## Acceptance Criteria

All three must pass for this spec to be considered complete.

### 1. Frontend — "Hello Redslim" page
- Navigating to `http://localhost:8080` renders a page with the heading **"Hello Redslim"**.
- On load, the page uses Axios to call `GET /redslim-hello` on the backend and displays the returned message below the heading.

### 2. Backend — `/redslim-hello` endpoint
- `GET http://localhost:8000/redslim-hello` returns HTTP `200` with JSON:
  ```json
  { "message": "Hello Redslim" }
  ```
- Registered via Django REST Framework.

### 3. Database — `redslim-exercise` accessible
- Connecting to `localhost:5432` with user `redslim` / password `redslim` succeeds.
- An empty database named `redslim-exercise` exists (no tables required beyond Django's after running `migrate`).