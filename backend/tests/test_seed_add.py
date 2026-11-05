"""Tests for `python -m scripts.seed --add`: it only ever ADDS missing demo users and projects.

The starting database mimics a real development database: three existing users with their own passwords,
and activity history written through the real API. Everything runs on the disposable test database.
"""

from collections.abc import Generator
from contextlib import nullcontext

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.progress_update import ProgressUpdate
from app.models.project import Project
from app.models.user import User, UserRole
from app.security import verify_password
from scripts import seed
from tests.conftest import CreateProject, CreateUser, auth_headers, valid_project_payload

TODAY = seed.today_in_app_timezone()
DEMO_EMAILS = {user.email for user in seed.USERS}
DEMO_PROJECT_COUNT = len(seed.PROJECTS)
DEMO_UPDATE_COUNT = sum(len(project.updates) for project in seed.PROJECTS)
DEMO_ACTIVITY_COUNT = DEMO_PROJECT_COUNT + DEMO_UPDATE_COUNT + 3  # + three status changes
OWN_PASSWORD = "MyOwnPass2026"


@pytest.fixture
def script_uses_test_db(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setattr(seed, "SessionLocal", lambda: nullcontext(db_session))


@pytest.fixture
def existing_data(client: TestClient, db_session: Session, create_user: CreateUser) -> list[User]:
    """Three non-demo users (one deactivated-then-reactivated) and activity history made through the API."""
    admin = create_user(
        role=UserRole.ADMIN, email="admin@example.com", name="Head Office", password=OWN_PASSWORD
    )
    manager = create_user(role=UserRole.MANAGER, email="verify.manager@example.com", password=OWN_PASSWORD)
    tester = create_user(role=UserRole.VIEWER, email="tester@example.com", password=OWN_PASSWORD)
    project_id = client.post(
        "/api/projects", json=valid_project_payload(), headers=auth_headers(manager)
    ).json()["id"]
    client.post(f"/api/projects/{project_id}/progress", json={"value": 600}, headers=auth_headers(manager))
    client.delete(f"/api/projects/{project_id}", headers=auth_headers(manager))
    client.patch(f"/api/users/{tester.id}", json={"role": "manager"}, headers=auth_headers(admin))
    client.patch(f"/api/users/{tester.id}", json={"is_active": False}, headers=auth_headers(admin))
    client.patch(f"/api/users/{tester.id}", json={"is_active": True}, headers=auth_headers(admin))
    db_session.expire_all()
    return [admin, manager, tester]


def snapshot(db: Session) -> dict:
    """Every column of every row that existed before --add (users including password hashes)."""
    db.expire_all()
    return {
        "users": [tuple(row) for row in db.execute(select(User.__table__).order_by(User.id))],
        "activity": [
            tuple(row) for row in db.execute(select(ActivityLog.__table__).order_by(ActivityLog.id))
        ],
        "projects": [tuple(row) for row in db.execute(select(Project.__table__).order_by(Project.id))],
        "progress": [
            tuple(row) for row in db.execute(select(ProgressUpdate.__table__).order_by(ProgressUpdate.id))
        ],
    }


def counts(db: Session) -> dict[str, int]:
    return {
        name: db.scalar(select(func.count()).select_from(model))
        for name, model in (
            ("users", User),
            ("projects", Project),
            ("progress", ProgressUpdate),
            ("activity", ActivityLog),
        )
    }


@pytest.fixture
def sql_statements(test_engine: Engine) -> Generator[list[str], None, None]:
    """Every SQL statement sent to the test database while the test runs."""
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _params, _context, _many) -> None:
        statements.append(statement.strip())

    event.listen(test_engine, "before_cursor_execute", capture)
    yield statements
    event.remove(test_engine, "before_cursor_execute", capture)


# ---------- existing data is never touched ----------


def test_add_keeps_every_existing_row_exactly(db_session: Session, existing_data: list[User]) -> None:
    before = snapshot(db_session)
    before_counts = counts(db_session)

    seed.add_missing(db_session, TODAY)

    after = snapshot(db_session)
    assert after["users"][: len(before["users"])] == before["users"]
    assert after["activity"][: len(before["activity"])] == before["activity"]
    assert counts(db_session) == {
        "users": before_counts["users"] + 4,
        "projects": before_counts["projects"] + DEMO_PROJECT_COUNT,
        "progress": before_counts["progress"] + DEMO_UPDATE_COUNT,
        "activity": before_counts["activity"] + DEMO_ACTIVITY_COUNT,
    }


def test_existing_users_keep_their_passwords_roles_and_status(
    db_session: Session, existing_data: list[User]
) -> None:
    seed.add_missing(db_session, TODAY)
    db_session.expire_all()

    roles = {}
    for user in existing_data:
        reloaded = db_session.get(User, user.id)
        assert verify_password(OWN_PASSWORD, reloaded.password_hash), reloaded.email
        assert not verify_password(seed.DEMO_PASSWORD, reloaded.password_hash), reloaded.email
        roles[reloaded.email] = (reloaded.role, reloaded.is_active)
    assert roles == {
        "admin@example.com": (UserRole.ADMIN, True),
        "verify.manager@example.com": (UserRole.MANAGER, True),
        "tester@example.com": (UserRole.MANAGER, True),
    }


def test_add_only_inserts_never_updates_deletes_or_truncates(
    db_session: Session, existing_data: list[User], sql_statements: list[str]
) -> None:
    seed.add_missing(db_session, TODAY)

    writes = [
        s.split()[0].upper()
        for s in sql_statements
        if s.split()[0].upper() in {"INSERT", "UPDATE", "DELETE", "TRUNCATE"}
    ]
    assert set(writes) == {"INSERT"}
    assert any("pg_advisory_xact_lock" in s for s in sql_statements)


# ---------- users ----------


def test_add_creates_the_four_demo_users_who_can_log_in(
    client: TestClient, db_session: Session, existing_data: list[User]
) -> None:
    seed.add_missing(db_session, TODAY)

    roles = {}
    for demo in seed.USERS:
        response = client.post("/api/auth/login", json={"email": demo.email, "password": seed.DEMO_PASSWORD})
        assert response.status_code == 200, demo.email
        roles[demo.email] = (response.json()["user"]["name"], response.json()["user"]["role"])
    assert roles == {
        "admin@vanatrack.demo": ("Asha Rao", "admin"),
        "manager@vanatrack.demo": ("Ravi Kumar", "manager"),
        "manager2@vanatrack.demo": ("Meera Iyer", "manager"),
        "viewer@vanatrack.demo": ("Vikram Shah", "viewer"),
    }


def test_existing_demo_user_is_reused_and_left_unchanged(
    db_session: Session, create_user: CreateUser, existing_data: list[User]
) -> None:
    own = create_user(
        role=UserRole.MANAGER, email="manager@vanatrack.demo", name="My Own Ravi", password=OWN_PASSWORD
    )
    own_row = tuple(db_session.execute(select(User.__table__).where(User.id == own.id)).one())

    summary = seed.add_missing(db_session, TODAY)

    db_session.expire_all()
    assert tuple(db_session.execute(select(User.__table__).where(User.id == own.id)).one()) == own_row
    assert "manager@vanatrack.demo" not in summary.splitlines()[0]
    assert db_session.scalar(select(func.count()).where(User.email.in_(DEMO_EMAILS))) == 4
    owned = db_session.scalar(select(func.count()).where(Project.owner_id == own.id))
    assert owned == sum(project.owner_key == "manager" for project in seed.PROJECTS) == 5


@pytest.mark.parametrize(
    ("role", "is_active", "message"),
    [(UserRole.VIEWER, True, "active viewer"), (UserRole.MANAGER, False, "inactive manager")],
)
def test_demo_owner_that_cannot_own_projects_stops_the_run(
    script_uses_test_db: None,
    db_session: Session,
    create_user: CreateUser,
    existing_data: list[User],
    capsys: pytest.CaptureFixture,
    role: UserRole,
    is_active: bool,
    message: str,
) -> None:
    create_user(role=role, is_active=is_active, email="manager2@vanatrack.demo", password=OWN_PASSWORD)
    before = snapshot(db_session)

    exit_code = seed.main(["--add"])

    assert exit_code == 1
    error = capsys.readouterr().err
    assert "manager2@vanatrack.demo" in error and message in error and "Nothing was changed" in error
    assert snapshot(db_session) == before


def test_existing_non_owner_demo_user_with_another_role_is_left_alone(
    db_session: Session, create_user: CreateUser, existing_data: list[User]
) -> None:
    viewer_as_manager = create_user(
        role=UserRole.MANAGER, email="viewer@vanatrack.demo", password=OWN_PASSWORD
    )

    seed.add_missing(db_session, TODAY)

    db_session.expire_all()
    assert db_session.get(User, viewer_as_manager.id).role == UserRole.MANAGER
    assert db_session.scalar(select(func.count()).where(User.email == "viewer@vanatrack.demo")) == 1


# ---------- projects and duplicates ----------


def test_running_add_twice_creates_no_duplicates(db_session: Session, existing_data: list[User]) -> None:
    first_summary = seed.add_missing(db_session, TODAY)
    after_first = snapshot(db_session)

    second_summary = seed.add_missing(db_session, TODAY)

    assert snapshot(db_session) == after_first
    assert "Created 10 projects" in first_summary
    assert second_summary.splitlines() == [
        "Created users: none (all demo users already existed).",
        "Created 0 projects, 0 progress updates and 0 activity entries.",
        f"Skipped 10 projects that already existed: {', '.join(sorted(p.name for p in seed.PROJECTS))}.",
    ]
    assert db_session.scalar(select(func.count(func.distinct(Project.name)))) == db_session.scalar(
        select(func.count()).select_from(Project)
    )


def test_project_with_a_demo_name_is_skipped_with_its_history_untouched(
    db_session: Session, create_project: CreateProject, existing_data: list[User]
) -> None:
    mine = create_project(existing_data[1], name="Western Ghats Reforestation", target_value=50)
    mine_row = tuple(db_session.execute(select(Project.__table__).where(Project.id == mine.id)).one())

    summary = seed.add_missing(db_session, TODAY)

    db_session.expire_all()
    assert tuple(db_session.execute(select(Project.__table__).where(Project.id == mine.id)).one()) == mine_row
    assert db_session.scalar(select(func.count()).where(ProgressUpdate.project_id == mine.id)) == 0
    assert db_session.scalar(select(func.count()).where(Project.name == "Western Ghats Reforestation")) == 1
    assert "Created 9 projects, 32 progress updates and 44 activity entries." in summary
    assert "Skipped 1 projects that already existed: Western Ghats Reforestation." in summary


def test_added_history_follows_the_rules_and_matches_activity(
    db_session: Session, existing_data: list[User]
) -> None:
    seed.add_missing(db_session, TODAY)
    demo_projects = list(
        db_session.scalars(select(Project).where(Project.name.in_(p.name for p in seed.PROJECTS)))
    )

    for project in demo_projects:
        updates = list(
            db_session.scalars(
                select(ProgressUpdate)
                .where(ProgressUpdate.project_id == project.id)
                .order_by(ProgressUpdate.recorded_at)
            )
        )
        previous_value = 0
        for update in updates:
            assert update.previous_value == previous_value, project.name
            [entry] = db_session.scalars(
                select(ActivityLog).where(
                    ActivityLog.action == ActivityAction.PROGRESS_LOGGED, ActivityLog.entity_id == update.id
                )
            )
            assert entry.created_at == update.recorded_at
            previous_value = update.value
        created = db_session.scalar(
            select(func.count()).where(
                ActivityLog.action == ActivityAction.CREATED, ActivityLog.entity_id == project.id
            )
        )
        assert created == 1, project.name
    owners = {project.owner.email for project in demo_projects}
    assert owners == {"manager@vanatrack.demo", "manager2@vanatrack.demo"}


def test_demo_scenarios_show_up_in_the_api_after_add(
    client: TestClient, db_session: Session, existing_data: list[User]
) -> None:
    seed.add_missing(db_session, TODAY)
    headers = auth_headers(existing_data[0])

    projects = {p["name"]: p for p in client.get("/api/projects", headers=headers).json()}
    attention = {item["name"] for item in client.get("/api/dashboard/attention", headers=headers).json()}

    assert projects["Western Ghats Reforestation"]["current_value"] == 600
    assert [name for name, p in projects.items() if p["is_behind_schedule"]] == ["Thar Solar Microgrid"]
    assert [name for name, p in projects.items() if p["is_target_exceeded"]] == ["Chennai Coastal Mangroves"]
    assert attention == {"Thar Solar Microgrid", "Pune Rainwater Harvesting"}


# ---------- command line ----------


def test_add_and_reset_together_are_rejected(
    script_uses_test_db: None, db_session: Session, existing_data: list[User], capsys: pytest.CaptureFixture
) -> None:
    before = snapshot(db_session)

    with pytest.raises(SystemExit) as exit_info:
        seed.main(["--add", "--reset"])

    assert exit_info.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err
    assert snapshot(db_session) == before


def test_add_prints_the_target_and_a_summary_but_no_password(
    script_uses_test_db: None, db_session: Session, existing_data: list[User], capsys: pytest.CaptureFixture
) -> None:
    exit_code = seed.main(["--add"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert output.startswith("Adding missing demo data to database '")
    created_line = f"Created users: {', '.join(user.email for user in seed.USERS)}."
    assert created_line in output
    assert seed.DEMO_PASSWORD not in output
    assert OWN_PASSWORD not in output


def test_no_flag_still_changes_nothing_and_mentions_both_modes(
    script_uses_test_db: None, db_session: Session, existing_data: list[User], capsys: pytest.CaptureFixture
) -> None:
    before = snapshot(db_session)

    exit_code = seed.main([])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Nothing was changed" in output and "--add" in output and "--reset" in output
    assert snapshot(db_session) == before
