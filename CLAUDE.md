# CLAUDE.md — VanaTrack

Rules for any AI coding assistant working in this repository. Read this file fully before writing any code.
Also read `ARCHITECTURE.md` and `DATABASE.md` before starting a task.

---

## 1. Project Context

- **What:** VanaTrack — a web app for Akshaya Vana Climate Ventures to manage environmental projects (afforestation, water, solar, waste) across locations and track their progress.
- **Why:** 48-hour technical assessment (Technical Assistant Intern). It is judged on **working features**, not visual polish or scalability.
- **Stack:** PostgreSQL · FastAPI (Python 3.11+) · React + Vite + TypeScript · Tailwind CSS · Recharts.
- **Deploy targets:** Neon (Postgres) · Render (API) · Vercel (frontend).

---

## 2. Priorities (in this order)

1. **Features work end to end** — UI → API → database → UI refresh.
2. **Correct data and permissions** — validation, error handling, auth, role checks.
3. **Readable code** — someone else must be able to explain every line in an interview.
4. **Deployable at all times** — `main` must always build and run.
5. Visual polish — only after 1–4 are done.

**Do NOT spend time on:** microservices, caching layers, queues, Docker orchestration, Kubernetes, horizontal scaling, premature abstraction, or perfection of design.

---

## 3. Non-Negotiable Requirements From the Assignment Brief

Every item below must be true at submission time.

### Frontend
- [ ] Clean, professional, consistent, **responsive** UI (desktop + mobile — test at 375px width).
- [ ] Sensible pages and navigation.
- [ ] Attention to usability details: loading states, empty states, error messages, confirm-before-delete.

### Backend & Database
- [ ] Working REST APIs for application data.
- [ ] Full **CRUD** (create, read, update, delete) on records.
- [ ] All data stored in **PostgreSQL** — no hardcoded data in the UI or API (seed scripts are fine).
- [ ] **Invalid input handled** — validated server-side, clear error messages shown in the UI.
- [ ] **User authentication** and **role-based access permissions**.

### Project Tracking & Dashboard
- [ ] Users can manage environmental projects and see their progress.
- [ ] Dashboard with meaningful stats and charts.
- [ ] Every dashboard value comes **from the database** and **updates when records change**.

### The Required Scenario (target 1,000 trees, 600 planted → updated to 850)
- [ ] Progress is stored as an **append-only log** of updates, never a silently overwritten number.
- [ ] Progress % is **derived** from the latest update and the target — never stored separately.
- [ ] After an update, the project page, project list, and dashboard all show the new value with no manual refresh.
- [ ] The full history (600 → 850, who changed it, when) is visible.
- [ ] Incorrect input (negative, non-numeric, decrease without a reason) is rejected with a clear message.
- [ ] A user modifying something they don't own gets **403** with a clear message, and the UI hides actions they can't perform.

### Submission
- [ ] Live website link (deployed, reachable).
- [ ] GitHub repository with complete source.
- [ ] `README.md` — project explanation, tech used, local run instructions.
- [ ] Test login credentials for each role.
- [ ] Demo video, max 5 minutes.
- [ ] "Not completed / would improve with more time" section in the README.
- [ ] **AI-assistance disclosure** in the README.

---

## 4. Git Workflow (mandatory)

### Branches
- `main` — always deployable. Never commit directly to `main`.
- Feature branches — **`feature/<feature-name>`**, kebab-case, e.g. `feature/auth`, `feature/projects-crud`, `feature/progress-tracking`.
- One feature per branch.

### Before starting any new feature
```bash
git checkout main
git pull origin main                 # skip if no remote yet
git status                           # must be clean
git branch --merged main             # previous feature/* branch must appear here
git log --oneline -5                 # confirm previous feature's merge commit exists
```
If the previous feature branch is **not** merged, stop and finish it first. Do not start a new feature on top of unmerged work.

### Commits
- Conventional commit format: `type(scope): short message`
  - `feat(projects): add create project endpoint`
  - `fix(auth): return 401 on expired token`
  - `test(progress): cover decrease-without-reason case`
  - `docs(readme): add deployment steps`
  - `chore(deps): add recharts`
  - `refactor(dashboard): extract kpi card component`
- Small, focused commits. Commit after each meaningful working step.
- Never commit `.env`, secrets, `node_modules`, `__pycache__`, `venv`, or build output.

### Finishing a feature
```bash
# all tests passing, app runs locally
git checkout main
git merge --no-ff feature/<feature-name> -m "merge: feature/<feature-name>"
git push origin main
git branch -d feature/<feature-name>   # optional, after confirming merge
```

---

## 5. Coding Standards

### General
- **Readable over clever.** Every line should be explainable in an interview.
- Descriptive names: `planted_count`, not `pc`. `getProjectProgress`, not `gpp`.
- Small functions — one job each. Aim for under ~40 lines per function.
- No dead code, no commented-out code blocks, no unused imports.
- Comments explain **why**, not what. Add a short docstring to every non-trivial function.
- No magic numbers — use named constants.
- Fail loudly and clearly. Never swallow exceptions silently.

### Backend (FastAPI)
- Layered structure: `routers/` (HTTP) → `services/` (business rules) → `models/` (SQLAlchemy). Routers stay thin.
- **Pydantic schemas** for every request and response body. Never return raw ORM objects without a response schema.
- All validation server-side, even if the frontend also validates.
- Permission checks live in reusable dependencies (`deps.py`), not copy-pasted into routes.
- Consistent error shape:
  ```json
  { "detail": "Human-readable message", "code": "PROGRESS_DECREASE_REQUIRES_NOTE" }
  ```
- Correct status codes: `200/201/204` success · `400` bad request · `401` not logged in · `403` not allowed · `404` not found · `409` conflict · `422` validation.
- Schema changes go through **Alembic migrations** only. Review every autogenerated migration: `downgrade` must also drop any enum types it created.
- Every foreign key declares an explicit `ON DELETE` rule (CASCADE / SET NULL / RESTRICT) per DATABASE.md section 3.5. Relationships to child tables use `passive_deletes=True`. `tests/test_deletion_policy.py` enforces this.
- Type hints on every function.
- Config from environment variables via `pydantic-settings`. Ship a `.env.example`.

### Frontend (React + TS)
- TypeScript everywhere. Avoid `any`.
- Feature-based folders: `src/features/<feature>/` holds that feature's components, hooks, and API calls.
- All server data through **TanStack Query**. After any mutation, invalidate related queries (`projects`, `project/:id`, `dashboard`) — this is how the dashboard stays in sync.
- One shared API client (`src/lib/api.ts`) that attaches the token and normalizes errors.
- Every data view handles 3 states: **loading**, **empty**, **error**.
- Forms: client-side validation that mirrors server rules, and server errors shown inline next to the field.
- Hide or disable actions the current user's role can't perform — but the backend is still the real guard.
- Tailwind only, no random inline styles. Mobile-first classes.

### Testing
- Backend: **pytest** with a test database. Every feature ships with tests for:
  - the happy path
  - invalid input (422 / 400)
  - unauthenticated (401)
  - unauthorized role or ownership (403)
  - not found (404)
- Frontend: manual test checklist per feature (desktop + 375px mobile). Write the checklist in the PR/merge message or `docs/test-log.md`.
- Never merge a feature with failing tests.

---

## 6. Definition of Done (per feature)

A feature is done only when **all** are true:
1. Backend endpoints implemented with validation and permission checks.
2. Migration created and applied (if the schema changed).
3. pytest tests written and passing.
4. Frontend UI wired to the real API, with loading/empty/error states.
5. Works on desktop and at 375px mobile width.
6. Manually tested end to end in the browser.
7. No console errors, no lint errors.
8. Committed with conventional commits, merged to `main` with `--no-ff`.
9. `main` still runs locally after the merge.

---

## 7. Things to Never Do

- Never commit to `main` directly.
- Never hardcode data in components (use the API + seed script).
- Never store derived values (progress %, totals) that can drift from source data.
- Never edit or delete a progress update to "fix" a number — add a correction entry instead.
- Never add a foreign key without an explicit `ON DELETE` rule.
- Never rely only on hidden buttons for security.
- Never commit secrets.
- Never introduce a new library without a clear reason stated in the commit message.
- Never start the next feature before the current branch is merged.
