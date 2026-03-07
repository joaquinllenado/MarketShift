# AGENTS.md

This file provides guidance to agents (i.e., ADAL) when working with code in this repository.

## Snapshot
- **Project**: MarketShift — React frontend + FastAPI/Prefect backend
- **Frontend**: React 19 + Vite + Tailwind CSS v4 (JavaScript)
- **Backend**: Python + FastAPI + Prefect (workflow orchestration)

---

## 1) Essential Commands

### Frontend (`frontend/`)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Dev server → http://localhost:5173
npm run build        # Production build → frontend/dist/
npm run preview      # Preview production build
```

### Backend (`backend/`)
```bash
cd backend
source venv/bin/activate    # Activate virtual env (REQUIRED before all commands)
uvicorn main:app --reload   # Dev server → http://localhost:8000
```

### Install backend dependencies
```bash
cd backend && source venv/bin/activate && pip install -r requirements.txt
```

### Run both together (dev)
1. Terminal 1: `cd backend && source venv/bin/activate && uvicorn main:app --reload`
2. Terminal 2: `cd frontend && npm run dev`

Frontend proxies `/api/*` → `http://localhost:8000/*` (configured in `vite.config.js`).

### Critical gotchas
- **Backend venv**: Always `source venv/bin/activate` before running Python commands.
- **Proxy rewrite**: Frontend strips `/api` prefix — `fetch('/api/hello')` hits backend `/hello`.
- **Tailwind v4**: Uses `@tailwindcss/vite` plugin (not PostCSS). CSS uses `@import "tailwindcss"` syntax.
- **Prefect flows run synchronously** inside FastAPI endpoints (no async). For production, use background tasks or Prefect deployments.

---

## 2) Non-Obvious Architecture

### Request flow
```
Browser → Vite dev server (:5173)
  → /api/* proxied to FastAPI (:8000) with /api prefix stripped
    → FastAPI endpoint calls Prefect @flow
      → Prefect @flow orchestrates @task(s) and returns result
    → JSON response back to browser
```

### Prefect integration
- `@flow` and `@task` decorators in `backend/main.py` are called directly from FastAPI route handlers.
- Prefect tracks execution, creates run graphs, and handles task retries/failures.
- Currently runs in **ephemeral mode** (no Prefect server). To enable the UI: `prefect server start` on port 4200.

### Frontend ↔ Backend contract
- Frontend calls `/api/hello` → Backend serves `GET /hello` → Returns `{ "message": "..." }`
- CORS is configured to allow `http://localhost:5173`.

---

## 3) Key Entry Points

| Component | Entry point | Purpose |
|-----------|------------|---------|
| Frontend app | `frontend/src/App.jsx` | Main React component |
| Frontend config | `frontend/vite.config.js` | Vite + Tailwind + API proxy |
| Frontend styles | `frontend/src/index.css` | Tailwind CSS import |
| Backend API | `backend/main.py` | FastAPI app + Prefect flows |
| Backend deps | `backend/requirements.txt` | Python dependencies |
| Backend venv | `backend/venv/` | Python virtual environment (not committed) |

---

## 4) Adding New Features

### New API endpoint + Prefect flow
1. Add `@task` function(s) in `backend/main.py` (or a new module)
2. Add `@flow` function that orchestrates the tasks
3. Add `@app.get` / `@app.post` route that calls the flow
4. Call from frontend via `fetch('/api/<route>')`

### New frontend page/component
1. Create component in `frontend/src/`
2. Use Tailwind utility classes for styling (no separate CSS files needed)
