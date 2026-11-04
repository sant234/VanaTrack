# VanaTrack

Environmental project management and progress tracking for Akshaya Vana Climate Ventures.

> 🚧 Work in progress. The full README (features, live link, test credentials, demo) is written in the final deployment step.

**Stack:** PostgreSQL · FastAPI (Python) · React + Vite + TypeScript · Tailwind CSS · TanStack Query · Recharts

Design docs: [ARCHITECTURE.md](ARCHITECTURE.md) · [DATABASE.md](DATABASE.md) · [CLAUDE.md](CLAUDE.md) (coding rules)

---

## Run it locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+

### 1. Database
Create a database user and two databases: one for the app, one only for tests.

```bash
sudo -u postgres psql -c "CREATE ROLE vanatrack WITH LOGIN PASSWORD 'vanatrack' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE vanatrack OWNER vanatrack;"
sudo -u postgres psql -c "CREATE DATABASE vanatrack_test OWNER vanatrack;"
```

### 2. Backend (API on http://localhost:8000)
```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                # then edit values if yours differ
alembic upgrade head                # create/update database tables
uvicorn app.main:app --reload --port 8000
```
Check it: open http://localhost:8000/api/health → `{"status":"ok","database":"ok"}`.
Interactive API docs: http://localhost:8000/docs

### 3. Frontend (app on http://localhost:5173)
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Checks

| What | Command (from the folder shown) |
|---|---|
| Backend tests | `backend/` → `pytest` |
| Backend lint | `backend/` → `ruff check . && ruff format --check .` |
| Frontend lint | `frontend/` → `npm run lint` |
| Frontend type check + build | `frontend/` → `npm run build` |

Tests use the separate `vanatrack_test` database. It is wiped and rebuilt from migrations on every run, so never point `TEST_DATABASE_URL` at real data.
