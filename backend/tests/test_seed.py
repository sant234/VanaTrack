"""Tests for scripts/seed.py: safety (no wipe without --reset), idempotence, API rules, and demo scenarios.

The script's session is pointed at the disposable test database, never DATABASE_URL.
"""

from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.activity_log import ActivityAction, ActivityLog
from app.models.progress_update import ProgressUpdate
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.security import create_access_token
from scripts import seed
from tests.conftest import CreateUser

PLAN_TODAY = date(2026, 11, 5)  # the date the approved seed plan was written for
IST = ZoneInfo("Asia/Kolkata")
EXPECTED_USERS = 4
EXPECTED_PROJECTS = 10
EXPECTED_UPDATES = 36
EXPECTED_ACTIVITY = EXPECTED_PROJECTS + EXPECTED_UPDATES + 3  # created + progress_logged + 3 status changes


@pytest.fixture
def script_uses_test_db(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setattr(seed, "SessionLocal", lambda: nullcontext(db_session))


@pytest.fixture
def seeded(db_session: Session) -> Session:
    """The demo data, seeded for the real today (so the API's "today" agrees with it)."""
    seed.reset_and_seed(db_session, seed.today_in_app_timezone())
    return db_session


def counts(db: Session) -> tuple[int, int, int, int]:
    return tuple(
        db.scalar(select(func.count()).select_from(model))
        for model in (User, Project, ProgressUpdate, ActivityLog)
    )


def headers_for(db: Session, email: str) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def project_named(db: Session, name: str) -> Project:
    return db.scalar(select(Project).where(Project.name == name))


# ---------- safety ----------


def test_without_reset_nothing_changes(
    script_uses_test_db: None, db_session: Session, create_user: CreateUser, capsys: pytest.CaptureFixture
) -> None:
    existing = create_user(email="keep.me@vanatrack.demo")

    exit_code = seed.main([])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Nothing was changed" in output
    assert "--reset" in output
    assert db_session.get(User, existing.id) is not None
    assert counts(db_session) == (1, 0, 0, 0)


def test_reset_prints_which_database_it_resets(
    script_uses_test_db: None, capsys: pytest.CaptureFixture
) -> None:
    exit_code = seed.main(["--reset"])

    output = capsys.readouterr().out
    test_url = make_url(get_settings().test_database_url)
    assert exit_code == 0
    assert output.startswith(f"Resetting database '{test_url.database}' on {test_url.host}:{test_url.port}")
    assert get_settings().test_database_url not in output
    assert seed.DEMO_PASSWORD not in output


def test_target_description_never_contains_the_password() -> None:
    url = make_url("postgresql+psycopg://neon_user:S3cret-Pa55word@ep-demo.neon.tech:5432/vanatrack_prod")
    session = SimpleNamespace(get_bind=lambda: SimpleNamespace(url=url))

    description = seed.describe_target(session)

    assert description == "database 'vanatrack_prod' on ep-demo.neon.tech:5432"
    assert "S3cret-Pa55word" not in description
    assert "neon_user" not in description


def test_reset_replaces_existing_data(db_session: Session, create_user: CreateUser) -> None:
    create_user(email="old@vanatrack.demo")

    seed.reset_and_seed(db_session, PLAN_TODAY)

    assert db_session.scalar(select(User).where(User.email == "old@vanatrack.demo")) is None
    assert counts(db_session) == (EXPECTED_USERS, EXPECTED_PROJECTS, EXPECTED_UPDATES, EXPECTED_ACTIVITY)


def _snapshot(db: Session) -> list:
    """Every seeded row except password hashes (bcrypt salts differ on every run by design)."""
    return [
        list(
            db.execute(select(User.id, User.email, User.name, User.role, User.created_at).order_by(User.id))
        ),
        list(db.execute(select(Project.__table__).order_by(Project.id))),
        list(db.execute(select(ProgressUpdate.__table__).order_by(ProgressUpdate.id))),
        list(db.execute(select(ActivityLog.__table__).order_by(ActivityLog.id))),
    ]


def test_running_twice_gives_the_same_result(db_session: Session) -> None:
    seed.reset_and_seed(db_session, PLAN_TODAY)
    first = _snapshot(db_session)

    seed.reset_and_seed(db_session, PLAN_TODAY)

    assert _snapshot(db_session) == first
    assert counts(db_session) == (EXPECTED_USERS, EXPECTED_PROJECTS, EXPECTED_UPDATES, EXPECTED_ACTIVITY)


def test_invalid_seed_data_changes_nothing(
    script_uses_test_db: None,
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    create_user: CreateUser,
    capsys: pytest.CaptureFixture,
) -> None:
    create_user(email="keep.me@vanatrack.demo")
    broken = replace(seed.PROJECTS[0], updates=[seed.SeedUpdate(100, 500), seed.SeedUpdate(50, 400)])
    monkeypatch.setattr(seed, "PROJECTS", [broken])

    exit_code = seed.main(["--reset"])

    assert exit_code == 1
    assert "not a correction" in capsys.readouterr().err
    assert counts(db_session) == (1, 0, 0, 0)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ([seed.SeedUpdate(400, 10)], "before the start date"),
        ([seed.SeedUpdate(-1, 10)], "in the future"),
        ([seed.SeedUpdate(100, 10), seed.SeedUpdate(100, 20)], "not later"),
        ([seed.SeedUpdate(100, 10_001)], "10x the target"),
        ([seed.SeedUpdate(100, 500), seed.SeedUpdate(50, 400, "short")], "not a correction"),
    ],
)
def test_check_history_rejects_what_the_api_would_reject(updates: list, message: str) -> None:
    project = replace(seed.PROJECTS[0], updates=updates)

    with pytest.raises(seed.SeedDataError, match=message):
        seed.check_history(project)


# ---------- users ----------


def test_demo_users_can_log_in(client: TestClient, seeded: Session) -> None:
    roles = {}
    for email in (
        "admin@vanatrack.demo",
        "manager@vanatrack.demo",
        "manager2@vanatrack.demo",
        "viewer@vanatrack.demo",
    ):
        response = client.post("/api/auth/login", json={"email": email, "password": seed.DEMO_PASSWORD})
        assert response.status_code == 200, email
        roles[email] = response.json()["user"]["role"]

    assert roles == {
        "admin@vanatrack.demo": "admin",
        "manager@vanatrack.demo": "manager",
        "manager2@vanatrack.demo": "manager",
        "viewer@vanatrack.demo": "viewer",
    }


# ---------- the history obeys the API's rules ----------


def test_every_progress_history_follows_the_api_rules(seeded: Session) -> None:
    now = datetime.now(UTC)
    for project in seeded.scalars(select(Project)):
        updates = list(
            seeded.scalars(
                select(ProgressUpdate)
                .where(ProgressUpdate.project_id == project.id)
                .order_by(ProgressUpdate.recorded_at)
            )
        )
        previous = None
        for update in updates:
            local_day = update.recorded_at.astimezone(IST).date()
            assert project.start_date <= local_day, project.name
            assert update.recorded_at <= now, project.name
            assert update.value <= project.target_value * 10, project.name
            assert update.previous_value == (previous.value if previous else 0), project.name
            assert previous is None or update.recorded_at > previous.recorded_at, project.name
            if previous and update.value < previous.value:
                assert update.is_correction and len(update.note.strip()) >= 10, project.name
            if project.status in seed.CLOSED_STATUSES:
                assert update.recorded_at < project.updated_at, project.name
            previous = update


def test_every_project_but_the_planned_one_has_3_to_8_updates(seeded: Session) -> None:
    for project in seeded.scalars(select(Project)):
        count = seeded.scalar(select(func.count()).where(ProgressUpdate.project_id == project.id))
        if project.status == ProjectStatus.PLANNED:
            assert count == 0  # the documented exception: it starts in the future
            assert project.start_date > seed.today_in_app_timezone()
        else:
            assert 3 <= count <= 8, project.name


def test_nashik_has_a_genuine_correction(seeded: Session) -> None:
    nashik = project_named(seeded, "Nashik Waste Segregation")
    chain = list(
        seeded.execute(
            select(ProgressUpdate.previous_value, ProgressUpdate.value, ProgressUpdate.is_correction)
            .where(ProgressUpdate.project_id == nashik.id)
            .order_by(ProgressUpdate.recorded_at)
        )
    )

    assert [tuple(row) for row in chain] == [
        (0, 2000, False),
        (2000, 4800, False),
        (4800, 4500, True),
        (4500, 6000, False),
        (6000, 7100, False),
    ]


# ---------- the demo scenarios, read through the real API ----------


def test_demo_scenarios_show_up_in_the_api(client: TestClient, seeded: Session) -> None:
    headers = headers_for(seeded, "viewer@vanatrack.demo")
    projects = {p["name"]: p for p in client.get("/api/projects", headers=headers).json()}

    brief = projects["Western Ghats Reforestation"]
    assert (brief["status"], brief["target_value"], brief["unit"], brief["current_value"]) == (
        "active",
        1000,
        "trees",
        600,
    )
    assert [name for name, p in projects.items() if p["is_behind_schedule"]] == ["Thar Solar Microgrid"]
    assert [name for name, p in projects.items() if p["is_target_exceeded"]] == ["Chennai Coastal Mangroves"]

    attention = client.get("/api/dashboard/attention", headers=headers).json()
    reasons = {item["name"]: item["reasons"] for item in attention}
    assert set(reasons) == {"Thar Solar Microgrid", "Pune Rainwater Harvesting"}
    assert (
        next(item for item in attention if item["name"] == "Pune Rainwater Harvesting")["days_since_update"]
        >= 30
    )


def test_projects_cover_five_states_both_managers_and_mixed_statuses(seeded: Session) -> None:
    projects = list(seeded.scalars(select(Project)))
    owners = {project.owner.email for project in projects}

    assert {project.state for project in projects} == {
        "Karnataka",
        "Maharashtra",
        "Tamil Nadu",
        "Rajasthan",
        "Uttarakhand",
    }
    assert owners == {"manager@vanatrack.demo", "manager2@vanatrack.demo"}
    assert sum(project.owner.email == "manager@vanatrack.demo" for project in projects) == 5
    assert {project.status for project in projects} == set(ProjectStatus)
    assert len({project.type for project in projects}) >= 4


def test_other_manager_gets_403_on_a_seeded_project(client: TestClient, seeded: Session) -> None:
    brief = project_named(seeded, "Western Ghats Reforestation")  # owned by manager@

    response = client.patch(
        f"/api/projects/{brief.id}",
        json={"name": "Taken"},
        headers=headers_for(seeded, "manager2@vanatrack.demo"),
    )

    assert response.status_code == 403


def test_the_brief_scenario_can_be_continued_live(client: TestClient, seeded: Session) -> None:
    brief = project_named(seeded, "Western Ghats Reforestation")

    response = client.post(
        f"/api/projects/{brief.id}/progress",
        json={"value": 850},
        headers=headers_for(seeded, "manager@vanatrack.demo"),
    )

    assert response.status_code == 201
    assert (response.json()["previous_value"], response.json()["value"]) == (600, 850)


# ---------- activity matches the history ----------


def test_every_project_and_update_has_one_matching_activity_entry(seeded: Session) -> None:
    for project in seeded.scalars(select(Project)):
        created = list(
            seeded.scalars(
                select(ActivityLog).where(
                    ActivityLog.action == ActivityAction.CREATED, ActivityLog.entity_id == project.id
                )
            )
        )
        assert len(created) == 1, project.name
        assert created[0].created_at == project.created_at
        assert created[0].user_id == project.owner_id
        assert created[0].details == {"name": project.name}

    for update in seeded.scalars(select(ProgressUpdate)):
        [entry] = seeded.scalars(
            select(ActivityLog).where(
                ActivityLog.action == ActivityAction.PROGRESS_LOGGED, ActivityLog.entity_id == update.id
            )
        )
        assert entry.created_at == update.recorded_at
        assert entry.project_id == update.project_id
        assert entry.user_id == update.created_by
        assert entry.details == {
            "from": update.previous_value,
            "to": update.value,
            "is_correction": update.is_correction,
        }

    assert counts(seeded)[3] == EXPECTED_ACTIVITY


# ---------- the approved plan's exact dates (for the day the plan was written) ----------


def test_plan_dates_for_2026_11_05(db_session: Session) -> None:
    seed.reset_and_seed(db_session, PLAN_TODAY)
    brief = project_named(db_session, "Western Ghats Reforestation")
    planned = project_named(db_session, "Rishikesh River Clean-up")
    brief_days = [
        update.recorded_at.astimezone(IST).date().isoformat()
        for update in db_session.scalars(
            select(ProgressUpdate)
            .where(ProgressUpdate.project_id == brief.id)
            .order_by(ProgressUpdate.recorded_at)
        )
    ]

    assert (brief.start_date, brief.end_date) == (date(2026, 1, 9), date(2027, 7, 3))
    assert brief.created_at == datetime(2026, 1, 2, 9, 0, tzinfo=IST)
    assert brief_days == ["2026-02-08", "2026-04-19", "2026-07-08", "2026-10-16"]
    assert (planned.start_date, planned.created_at.astimezone(IST).date()) == (
        date(2026, 12, 5),
        date(2026, 11, 2),
    )


@pytest.mark.parametrize(
    ("name", "status", "changed_at"),
    [
        ("Dehradun School Rooftop Solar", "completed", datetime(2026, 10, 1, 17, 0, tzinfo=IST)),
        ("Jaisalmer Check Dams", "cancelled", datetime(2026, 8, 22, 17, 0, tzinfo=IST)),
        ("Nilgiris Shola Restoration", "on_hold", datetime(2026, 9, 16, 17, 0, tzinfo=IST)),
    ],
)
def test_status_changes_are_logged_on_their_dates(
    db_session: Session, name: str, status: str, changed_at: datetime
) -> None:
    seed.reset_and_seed(db_session, PLAN_TODAY)
    project = project_named(db_session, name)

    [entry] = db_session.scalars(
        select(ActivityLog).where(
            ActivityLog.action == ActivityAction.UPDATED, ActivityLog.entity_id == project.id
        )
    )

    assert entry.created_at == changed_at
    assert project.updated_at == changed_at
    assert entry.user_id == project.owner_id
    assert entry.details == {"name": name, "changes": {"status": {"from": "active", "to": status}}}
