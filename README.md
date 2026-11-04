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

`JWT_SECRET` must be at least 32 characters or the API will not start. Generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Create the first admin
Sign-up always creates **viewer** accounts. Create an admin (or promote an existing account) from `backend/`:
```bash
python -m scripts.create_admin --email admin@example.com --name "Head Office"
```
You will be asked for the password at a hidden prompt (typed twice). On a server without a keyboard,
set it only for that one command:
```bash
ADMIN_PASSWORD='...' python -m scripts.create_admin --email admin@example.com --name "Head Office" --password-from-env
```
There is deliberately no `--password` option: command-line arguments end up in shell history and are
visible to other users via `ps`. The script never prints the password.

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

---

## Roles

| Role | Can do |
|---|---|
| **Admin** | Everything, including managing users |
| **Manager** | Create projects; edit, delete and log progress on their **own** projects |
| **Viewer** | Read-only. Every new sign-up starts here |

The backend enforces every permission (401 = not logged in, 403 = role not allowed). The frontend also hides
actions a role cannot perform, but that is only for convenience, never the security boundary.

An owner who is later demoted to viewer loses edit rights on their projects (viewers are always read-only).

---

## Projects

| Rule | Detail |
|---|---|
| **Who can create** | Managers and admins. The creator becomes the owner; ownership cannot be changed by editing |
| **Who can edit/delete** | The owning manager, or any admin. Others get `403 "You can only modify projects you own."` |
| **Validation** | Name 3–150 chars · target a whole number > 0 · end date on/after start date (also checked against saved dates on partial edits) · state from the official list of 28 states + 8 UTs · budget ≥ 0 with at most 2 decimals |
| **Progress** | Never stored on the project. `current_value` is the latest progress update; `progress_percent`, `expected_percent`, `is_behind_schedule` and `is_target_exceeded` are calculated on every request in `services/progress_service.py` (behind = active and more than 10 points behind the timeline; "today" uses India time) |
| **List filters** | `search`, `type`, `status`, `state`, `mine`, `sort` (`name`, `created_at`, `end_date`, `progress`) + `order`. In the UI they live in the URL, so refresh and shared links keep them |

### Deletion policy
Deleting a project is one transaction, and the database decides what happens to related rows:
records that belong to the project are deleted with it (**CASCADE**), history entries are kept with the
link cleared (**SET NULL**), and a user who owns projects cannot be deleted (**RESTRICT**, deactivate instead).
Tests read the live schema and fail if any foreign key lacks an explicit rule or a deleted project leaves
references behind. Details: [DATABASE.md, section 3.5](DATABASE.md).

---

## How the 600 → 850 scenario is handled

> *A project has a target of 1,000 trees and 600 have been planted. Later the number is updated to 850.*

**Progress is an append-only log, not a number that gets overwritten.** Each update stores the new running
total ("850 planted so far") and the total just before it, which the server fills in itself. Updating 600 to 850
adds a second row, `600 → 850 (+250)`, logged by a named user at a recorded time. The first row (`0 → 600`) is
never changed, so the full history stays visible on the project page as a timeline and a chart.

**Every number is derived from that log, never stored separately.** The project's current value is simply
its latest update, and progress % is `current ÷ target` (850 ÷ 1,000 = **85%**). The project page, the project
list, sorting by progress and (Prompt 4) the dashboard all read the same database query, so they cannot
disagree. After saving, the app refreshes every screen that shows project numbers before it confirms the save,
so 85% appears everywhere at once, without reloading the page.

**Wrong or suspicious input is rejected with a clear message:**

| Input | Result |
|---|---|
| `-5`, `12.5`, `"850"` | 422, "Enter a whole number" |
| 850 again | 400 `PROGRESS_NO_CHANGE` |
| 700 (a drop) without explanation | 400 `PROGRESS_DECREASE_REQUIRES_NOTE`. The form asks to mark it as a **correction** with a reason of at least 10 characters (e.g. *"50 saplings died, recount"*). It is then saved as `850 → 700 (−150)` with a *Correction* badge |
| 10,001 on a 1,000 target | 400 `PROGRESS_UNREALISTIC` (likely an extra zero) |
| 1,120 on a 1,000 target | Allowed: real over-achievement shows **112%** and *Exceeded target* |
| A future date, or a date before the previous update | 422 |
| Any update on a completed or cancelled project | 400 `PROJECT_CLOSED` |

**Unauthorized changes are refused.** Only the project's owning manager or an admin can log progress. A viewer
or another manager gets **403 "You can only modify projects you own."**, and the *Log progress* button is not
shown to them. Updates cannot be edited at all; an admin can only undo the **newest** entry, so the history
always reads correctly. The rules are enforced on the server and again by database constraints.

---

## Dashboard

The home page (`/`) shows live figures for every project, or one project type (the filter is kept in the URL).
Nothing on it is stored: each request recalculates from the projects and progress updates, using the same query
as the project list, so the two always agree.

| Widget | What it shows |
|---|---|
| **Key figures** | Total and active projects · average completion · trees planted · estimated CO₂ absorbed per year (trees × 21 kg, configurable) · behind schedule · exceeded target |
| **Progress by project** | Top 10 projects by completion; each bar is coloured *and* labelled On track / Behind / Exceeded |
| **Average completion over time** | The last 12 months, carrying each project's last total forward; includes a table view |
| **Projects by type / Completion by state** | Ranked bars with counts, average completion and trees planted |
| **Needs attention** | Projects behind schedule, or active with no update for 30+ days, each linking to its page |

**Why "average completion" and not "total achieved ÷ total target":** projects use different units (trees, kW,
kL of water), so adding them together would be meaningless. Each project's completion % is unit-free; the dashboard
averages them, counting each project at most 100%, and leaves out cancelled and not-yet-started projects.

In the brief's scenario, updating 600 → 850 changes *Trees planted* to **850** (not 1,450) and the project's
completion to 85%. The dashboard refreshes right after a save, and also when you return to its tab after logging
progress somewhere else.

---

## Known trade-offs (to revisit)

- **Login token in `localStorage`.** Simple and works across separate frontend/backend domains, but readable by
  any injected script. An httpOnly cookie would be safer against XSS; it needs extra CSRF and cross-site cookie setup.
