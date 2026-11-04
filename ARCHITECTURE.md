# ARCHITECTURE.md — VanaTrack

Environmental project management and progress tracking for Akshaya Vana Climate Ventures.

---

## 1. Product Concept

**One-liner:** Track every environmental project, every site, every update — with a live dashboard that never lies.

**Core idea:** A project has a **target** (e.g. 1,000 trees). Field teams log **progress updates** over time. Everything else (progress %, dashboard totals, behind-schedule flags, charts) is **derived** from those updates, so it is always consistent.

**Users**
| Role | Who | Can do |
|---|---|---|
| **Admin** | Head office | Everything, including managing users and roles |
| **Manager** | Project lead | Create projects, edit/delete **own** projects, log progress on own projects |
| **Viewer** | Stakeholder / donor / auditor | Read-only access to projects and dashboard |

---

## 2. Feature Map

### Group A — Foundation
- **A1. Project setup** — monorepo scaffold, DB connection, migrations, health check.
- **A2. Authentication & roles** — register, login, JWT, current user, role guards.

### Group B — Core Tracking
- **B1. Projects CRUD** — create, list, view, edit, delete; search and filters; ownership rules.
- **B2. Progress tracking** — append-only progress log, corrections, history timeline, derived %.

### Group C — Insight
- **C1. Dashboard** — KPI cards and charts computed live from the DB.
- **C2. Activity log** — who changed what and when, across the organization.

### Group D — Administration & Usability
- **D1. User management** — admin lists users, changes roles, deactivates accounts.
- **D2. Export & polish** — CSV export, seed data, responsive pass, empty/error states.

### Group E — Ship
- **E1. Deployment & docs** — Neon + Render + Vercel, README, credentials, demo script.

---

## 3. System Architecture

```
┌──────────────────────────────┐        HTTPS / JSON         ┌──────────────────────────────┐
│  Frontend (Vercel)           │  ───────────────────────▶   │  Backend API (Render)        │
│  React + Vite + TS           │   Authorization: Bearer JWT │  FastAPI                     │
│  TanStack Query (cache)      │  ◀───────────────────────   │  routers → services → models │
│  Tailwind + Recharts         │                             │  Pydantic validation         │
└──────────────────────────────┘                             └──────────────┬───────────────┘
                                                                            │ SQLAlchemy
                                                                            ▼
                                                             ┌──────────────────────────────┐
                                                             │  PostgreSQL (Neon)           │
                                                             │  users · projects ·          │
                                                             │  progress_updates ·          │
                                                             │  activity_logs               │
                                                             └──────────────────────────────┘
```

---

## 4. Repository Layout

```
vanatrack/
├── CLAUDE.md
├── ARCHITECTURE.md
├── DATABASE.md
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # env settings (pydantic-settings)
│   │   ├── database.py          # engine, SessionLocal, get_db
│   │   ├── deps.py              # get_current_user, require_role, require_project_owner
│   │   ├── security.py          # password hashing, JWT create/verify
│   │   ├── errors.py            # AppError + exception handlers (consistent error shape)
│   │   ├── models/              # SQLAlchemy models (one file per table)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # business rules (progress validation, dashboard queries)
│   │   └── routers/             # auth, users, projects, progress, dashboard, activity, export
│   ├── alembic/                 # migrations
│   ├── scripts/seed.py          # sample data + test users
│   ├── tests/                   # pytest
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── lib/                 # api.ts (fetch client), queryClient.ts, format.ts
    │   ├── components/          # shared UI: Button, Card, Modal, Badge, ProgressBar, Toast
    │   ├── layouts/             # AppLayout (sidebar desktop / bottom-nav or drawer mobile)
    │   ├── features/
    │   │   ├── auth/            # LoginPage, RegisterPage, AuthContext, ProtectedRoute
    │   │   ├── projects/        # ProjectsListPage, ProjectDetailPage, ProjectForm
    │   │   ├── progress/        # LogProgressModal, ProgressTimeline, ProgressChart
    │   │   ├── dashboard/       # DashboardPage, KpiCard, charts
    │   │   ├── activity/        # ActivityPage
    │   │   └── users/           # UsersAdminPage
    │   ├── App.tsx              # routes
    │   └── main.tsx
    └── .env.example
```

---

## 5. Pages & Navigation

| Route | Page | Access |
|---|---|---|
| `/login` | Login | Public |
| `/register` | Register (creates a Viewer) | Public |
| `/` | Dashboard | All logged-in |
| `/projects` | Projects list — search, filter by type/status/state, sort | All logged-in |
| `/projects/new` | Create project | Manager, Admin |
| `/projects/:id` | Project detail — info, progress bar, log update, history timeline, chart | All logged-in |
| `/projects/:id/edit` | Edit project | Owner, Admin |
| `/activity` | Organization-wide activity log | All logged-in |
| `/users` | User management | Admin |
| `*` | 404 page | — |

**Layout:** sidebar on desktop, collapsible drawer on mobile. Top bar shows user name + role badge + logout.

---

## 6. API Design

Base path: `/api`. All endpoints except auth and health require `Authorization: Bearer <token>`.

### Auth
| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account (role = viewer) |
| POST | `/auth/login` | Return JWT + user |
| GET | `/auth/me` | Current user |

### Projects
| Method | Path | Who |
|---|---|---|
| GET | `/projects?search=&type=&status=&state=&sort=` | All |
| POST | `/projects` | Manager, Admin |
| GET | `/projects/{id}` | All |
| PATCH | `/projects/{id}` | Owner, Admin |
| DELETE | `/projects/{id}` | Owner, Admin |

Project responses always include derived fields: `current_value`, `progress_percent`, `expected_percent`, `is_behind_schedule`, `last_updated_at`.

### Progress
| Method | Path | Who |
|---|---|---|
| GET | `/projects/{id}/progress` | All |
| POST | `/projects/{id}/progress` | Owner, Admin |
| DELETE | `/projects/{id}/progress/{update_id}` | Admin only, **newest entry only** (logged to activity) |

### Dashboard
| Method | Path | Returns |
|---|---|---|
| GET | `/dashboard/summary` | KPI numbers |
| GET | `/dashboard/by-type` | Count + avg progress per project type |
| GET | `/dashboard/by-state` | Count + total achieved per state |
| GET | `/dashboard/trend` | Monthly cumulative achieved (last 12 months) |
| GET | `/dashboard/attention` | Projects behind schedule or with no update in 30 days |

### Activity, Users, Export, Health
| Method | Path | Who |
|---|---|---|
| GET | `/activity?limit=&project_id=` | All |
| GET | `/users` | Admin |
| PATCH | `/users/{id}` | Admin (role, is_active) |
| GET | `/export/projects.csv` | All |
| GET | `/health` | Public |

---

## 7. Key Business Rules

### 7.1 Progress model (the 600 → 850 scenario)
1. A progress update records the **new cumulative total** ("850 trees planted so far"), not a delta. This matches how field teams report and avoids arithmetic errors.
2. Each update stores `previous_value` (snapshot of the total before it) so the history reads `600 → 850 (+250)`.
3. **Current value** = value of the most recent update (by `recorded_at`, then `id`). Zero if none.
4. **Progress %** = `current_value / target_value × 100`, computed at read time.
5. After a successful update, the frontend invalidates `projects`, `project/:id`, `progress/:id`, `dashboard`, and `activity` queries — every screen shows 850 immediately.

### 7.2 Validation
| Case | Result |
|---|---|
| Value negative / not an integer | 422 with field message |
| Value lower than current (e.g. 850 → 700) without `is_correction=true` and a note (min 10 chars) | 400 `PROGRESS_DECREASE_REQUIRES_NOTE` |
| Value equals current | 400 `PROGRESS_NO_CHANGE` |
| Value above target | Allowed. Progress shown as e.g. 112% with an **"Exceeded target"** badge (overachievement is real) |
| Value above 10× target | 400 `PROGRESS_UNREALISTIC` (likely typo, e.g. extra zero) |
| `recorded_at` in the future, or without a timezone | 422 |
| `recorded_at` before the latest update, or before the project start date | 422 (keeps the log in time order, so `previous_value` is always the total just before) |
| Logging progress on a `completed` or `cancelled` project | 400 `PROJECT_CLOSED` |
| Correction (`is_correction=true`) with a note under 10 characters | 422 on `note` |
| Value above 2,000,000,000 (INTEGER safety) or not a whole number | 422 |
| Deleting any update except the newest | 400 `PROGRESS_NOT_LATEST` (add a correction instead) |
| Project `end_date` before `start_date` | 422 |
| Changing a project's `target_value` below its current value | Allowed, but response flags it; UI warns before saving |

### 7.3 Schedule tracking
- `expected_percent` = elapsed days / total days × 100 (clamped 0–100).
- `is_behind_schedule` = status is active AND `progress_percent < expected_percent − 10`.

### 7.4 Permissions
| Action | Admin | Manager (owner) | Manager (not owner) | Viewer |
|---|---|---|---|---|
| View projects/dashboard | ✅ | ✅ | ✅ | ✅ |
| Create project | ✅ | ✅ | ✅ | ❌ 403 |
| Edit / delete project | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Log progress | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Delete progress entry | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |
| Manage users | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |

- No token / expired token → **401**, frontend redirects to `/login`.
- Deactivated user → **401** on login.
- Admin cannot demote or deactivate themselves (prevents lockout).

### 7.5 Activity logging
Every create/update/delete on projects, every progress update, and every role change writes one `activity_logs` row in the **same transaction** as the change.

---

## 8. Dashboard Design

Every endpoint accepts `?type=` and is computed per request from the **same query and rules as the project
list** (`progress_service.select_projects_with_progress` + `build_progress`), so the dashboard and the project
pages can never disagree. No totals are cached or stored.

**Completion is unit-free.** Projects are measured in different units (trees, kW, kL water ...), so
"sum achieved / sum target" across projects would add trees to kilowatts. Instead each project's completion %
is used, **capped at 100%** (one over-achiever cannot hide projects that are behind), and averaged.
A project **counts toward completion** only if it is not cancelled (it will never finish) and has started
(0% is expected before the start date). Cancelled projects still count in "Total projects".

**KPI cards (row 1)**
- Total projects · Active projects
- Average completion % (of counted projects)
- Trees planted (sum of current values where `lower(unit) = 'trees'`; units keep their capitalisation, e.g. kW)
- Projects behind schedule · Projects that exceeded their target
- Est. CO₂ absorbed per year (trees × `CO2_KG_PER_TREE_PER_YEAR`, in tonnes, labelled "estimate")

**Charts (row 2)**
- **Bars:** progress % per project (top 10, coloured AND labelled on track / behind / exceeded; palette checked for colour blindness)
- **Line:** average completion at each month-end for the last 12 months (current month = today); a month with no update carries the previous total forward; months before any project started are gaps. A table view sits under the chart.
- **Ranked bars:** projects by type (count + average completion). Ranked bars replace the originally planned donut: they compare categories more exactly and print each count.
- **Bars:** average completion by state, with project count and trees planted

**Needs attention (row 3)**
- Projects that are **behind schedule**, or **active with no progress update for 30+ days** (counted from the start date if nothing was ever logged), furthest behind first, each linking to the project.

**Freshness:** every save invalidates the dashboard cache, and dashboard queries refetch whenever the tab
regains focus (`refetchOnWindowFocus: 'always'`), so progress logged in another tab appears on return.

---

## 9. Error Handling

- Backend: one `AppError(status, code, message)` class + global handlers → always `{ "detail", "code" }`. Pydantic 422s are reshaped into `{ "detail", "code": "VALIDATION_ERROR", "fields": {field: message} }`.
- Frontend: `api.ts` throws a typed `ApiError`. Forms map `fields` to inline errors. Other errors show a toast. A 401 clears the session and redirects to login.

---

## 10. Deployment

| Piece | Platform | Notes |
|---|---|---|
| Database | Neon Postgres | Copy connection string into Render env |
| API | Render web service | Build: `pip install -r requirements.txt`; start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Frontend | Vercel | Root `frontend/`, env `VITE_API_URL`, SPA rewrite to `index.html` |

Env vars: `DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, `CO2_KG_PER_TREE_PER_YEAR`.

Note: Render free tier sleeps when idle. Before the reviewers check, hit `/api/health` to wake it, and mention the cold start in the README.

---

## 11. Out of Scope (deliberately)

- Microservices, caching, queues, websockets — TanStack Query invalidation is enough for "updates when records change".
- File/photo uploads, maps, multi-tenancy, email verification, password reset.
- These go in the README's "What I would improve with more time" section.
