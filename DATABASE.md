# DATABASE.md — VanaTrack

PostgreSQL schema. Four tables. Progress is **append-only**; all totals and percentages are **derived at read time**.

---

## 1. Entity Relationship Diagram

```
┌─────────────────┐ 1        * ┌──────────────────┐ 1        * ┌────────────────────┐
│ users           │────────────│ projects         │────────────│ progress_updates   │
│ id (PK)         │  owner_id  │ id (PK)          │ project_id │ id (PK)            │
│ name            │            │ owner_id (FK)    │            │ project_id (FK)    │
│ email (UQ)      │            │ name             │            │ value              │
│ password_hash   │            │ type             │            │ previous_value     │
│ role            │            │ status           │            │ is_correction      │
│ is_active       │            │ target_value     │            │ note               │
│ created_at      │            │ unit             │            │ recorded_at        │
└────────┬────────┘            │ state, district  │            │ created_by (FK)    │
         │                     │ start/end_date   │            │ created_at         │
         │                     └────────┬─────────┘            └────────────────────┘
         │ 1                            │ 0..1
         │                              │
         │ *                            │ *
┌────────┴──────────────────────────────┴─────┐
│ activity_logs                                │
│ id · user_id (FK) · project_id (FK, null ok) │
│ action · entity_type · entity_id · details   │
│ created_at                                   │
└──────────────────────────────────────────────┘
```

---

## 2. Enums

```sql
CREATE TYPE user_role       AS ENUM ('admin', 'manager', 'viewer');
CREATE TYPE project_type    AS ENUM ('afforestation', 'water_conservation', 'solar', 'waste_management', 'other');
CREATE TYPE project_status  AS ENUM ('planned', 'active', 'on_hold', 'completed', 'cancelled');
CREATE TYPE activity_action AS ENUM ('created', 'updated', 'deleted', 'progress_logged', 'progress_deleted', 'role_changed', 'user_deactivated');
```

---

## 3. Tables

### 3.1 `users`
```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100)  NOT NULL,
    email           VARCHAR(255)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    role            user_role     NOT NULL DEFAULT 'viewer',
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
```
- Emails stored lowercase (normalized in the service layer).
- Self-registration always creates `viewer`; only an admin promotes.

### 3.2 `projects`
```sql
CREATE TABLE projects (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(150)    NOT NULL,
    description     TEXT,
    type            project_type    NOT NULL,
    status          project_status  NOT NULL DEFAULT 'planned',
    target_value    INTEGER         NOT NULL CHECK (target_value > 0),
    unit            VARCHAR(30)     NOT NULL,          -- 'trees', 'kL water', 'kW', 'kg waste' (case kept; compare case-insensitively)
    state           VARCHAR(60)     NOT NULL,
    district        VARCHAR(60),
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    budget_inr      NUMERIC(14, 2)  CHECK (budget_inr IS NULL OR budget_inr >= 0),
    owner_id        INTEGER         NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT end_after_start CHECK (end_date >= start_date)
);

CREATE INDEX idx_projects_owner  ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_type   ON projects(type);
```
- **No `current_value` or `progress_percent` column.** Both are derived (see section 4).
- `ON DELETE RESTRICT` on owner: an owner can't be hard-deleted while owning projects (users are deactivated instead).

### 3.3 `progress_updates` — append-only
```sql
CREATE TABLE progress_updates (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    value           INTEGER      NOT NULL CHECK (value >= 0),   -- new cumulative total
    previous_value  INTEGER      NOT NULL CHECK (previous_value >= 0),
    is_correction   BOOLEAN      NOT NULL DEFAULT FALSE,
    note            TEXT,
    recorded_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),        -- when it happened in the field
    created_by      INTEGER      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),        -- when it was entered
    CONSTRAINT correction_needs_note CHECK (is_correction = FALSE OR length(note) >= 10)
);

CREATE INDEX idx_progress_project_recorded ON progress_updates(project_id, recorded_at DESC, id DESC);
```
- No `UPDATE` endpoint exists for this table. Mistakes are fixed with a new correction entry.
- Only an admin can delete an entry, and the deletion is written to `activity_logs`.
- Deleting a project cascades its updates (the project deletion itself is logged).

### 3.4 `activity_logs`
```sql
CREATE TABLE activity_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER          NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    project_id      INTEGER          REFERENCES projects(id) ON DELETE SET NULL,
    action          activity_action  NOT NULL,
    entity_type     VARCHAR(30)      NOT NULL,   -- 'project', 'progress_update', 'user'
    entity_id       INTEGER          NOT NULL,
    details         JSONB            NOT NULL DEFAULT '{}',  -- e.g. {"from": 600, "to": 850}
    created_at      TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX idx_activity_created ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_project ON activity_logs(project_id);
```
- `project_id` becomes NULL when a project is deleted, so the "deleted project X" entry survives. Store the project name in `details`.

---

## 3.5 Deletion Policy (mandatory for every foreign key)

Every foreign key states **explicitly** what happens when the row it points to is deleted.
PostgreSQL's silent default (`NO ACTION`) is never used.

| Rule | Meaning | Used for |
|---|---|---|
| **CASCADE** | Delete the child rows too | Records that are meaningless without their parent: `progress_updates.project_id` |
| **SET NULL** | Keep the row, clear the link | History that must survive: `activity_logs.project_id` (the project name is copied into `details`) |
| **RESTRICT** | Refuse the delete | `projects.owner_id`, `progress_updates.created_by`, `activity_logs.user_id`. Users are **deactivated**, never deleted |

How this is kept true:
- The rule lives **in the database** (`ON DELETE ...`), so even a manual SQL delete cannot leave orphans.
- SQLAlchemy relationships to child tables use `passive_deletes=True`, so the ORM leaves deletion to the database instead of issuing its own conflicting `UPDATE`/`DELETE` statements.
- Deleting a project is one transaction: everything goes, or nothing does.
- `backend/tests/test_deletion_policy.py` reads the **live schema** and fails if:
  - any foreign key uses `NO ACTION`;
  - any foreign key to `projects` is not `CASCADE` or `SET NULL`;
  - after deleting a project through the API, any table still references its id.

New tables in later prompts are covered by these tests automatically.

---

## 4. Derived Values (never stored)

### Current value per project
```sql
-- Latest update per project; 0 if the project has none.
SELECT p.id,
       COALESCE(latest.value, 0)                                   AS current_value,
       ROUND(COALESCE(latest.value, 0) * 100.0 / p.target_value, 1) AS progress_percent,
       latest.recorded_at                                           AS last_updated_at
FROM projects p
LEFT JOIN LATERAL (
    SELECT value, recorded_at
    FROM progress_updates pu
    WHERE pu.project_id = p.id
    ORDER BY pu.recorded_at DESC, pu.id DESC
    LIMIT 1
) latest ON TRUE;
```
Implement this once in `services/progress_service.py` and reuse it in project list, project detail, dashboard, and CSV export, so every screen uses the same number.

### Expected % (schedule)
```sql
LEAST(100, GREATEST(0,
  (CURRENT_DATE - p.start_date) * 100.0 / NULLIF(p.end_date - p.start_date, 0)
)) AS expected_percent
```

---

## 5. Walkthrough: 600 → 850

| Step | Action | `progress_updates` row | Derived result |
|---|---|---|---|
| 1 | Project created, target 1,000 trees | — | current 0, 0% |
| 2 | Manager logs 600 | `value=600, previous_value=0` | current 600, 60% |
| 3 | Manager logs 850 | `value=850, previous_value=600` | current 850, 85% |
| 4 | Manager tries 700, no note | rejected 400 | unchanged 85% |
| 5 | Manager logs 700, `is_correction`, note "50 saplings died, recount" | `value=700, previous_value=850, is_correction=true` | current 700, 70% |
| 6 | Viewer tries to log 900 | rejected 403 | unchanged |

Each successful step also writes an `activity_logs` row in the same transaction.

---

## 6. Seed Data (`backend/scripts/seed.py`)

**Users** (password for all: `Demo@1234`)
| Email | Role |
|---|---|
| admin@vanatrack.demo | admin |
| manager@vanatrack.demo | manager |
| manager2@vanatrack.demo | manager |
| viewer@vanatrack.demo | viewer |

**Projects:** ~10 across Karnataka, Maharashtra, Tamil Nadu, Rajasthan, and Uttarakhand. Mixed types and statuses. Include:
- One project matching the brief: **target 1,000 trees, at 600**.
- One **behind schedule**.
- One **exceeded target**.
- One with **no updates in 30+ days**.
- Owners split between `manager` and `manager2`, so 403 can be demoed.

**Progress history:** 3–8 updates per project spread over the past 12 months, so the trend chart has shape.

The seed script must be **idempotent**: it truncates and reseeds, and is safe to run repeatedly.
