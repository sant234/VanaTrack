"""Tests for the activity log: one entry per change, nothing for rejected requests, and GET /activity."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.activity import ACTIVITY_DEFAULT_LIMIT, ACTIVITY_MAX_LIMIT
from app.services.activity_service import SUMMARY_BUILDERS, build_summary
from tests.conftest import CreateProject, CreateUser, auth_headers, valid_project_payload

MISSING_ID = 999_999
ACTIVITY_URL = "/api/activity"


@pytest.fixture
def manager(create_user: CreateUser) -> User:
    return create_user(role=UserRole.MANAGER, name="Field Manager")


@pytest.fixture
def project(create_project: CreateProject, manager: User) -> Project:
    return create_project(manager, name="Western Ghats", target_value=1000, unit="trees")


def activity_rows(db_session: Session) -> list[ActivityLog]:
    """Every activity row, oldest first."""
    return list(db_session.scalars(select(ActivityLog).order_by(ActivityLog.id)))


def activity_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(ActivityLog))


def log(client: TestClient, user: User, project_id: int, **body: object):
    return client.post(f"/api/projects/{project_id}/progress", json=body, headers=auth_headers(user))


def read_activity(client: TestClient, user: User, query: str = ""):
    return client.get(f"{ACTIVITY_URL}{query}", headers=auth_headers(user))


# ---------- each write path writes exactly one entry ----------


def test_creating_a_project_records_one_created_entry(
    client: TestClient, db_session: Session, manager: User
) -> None:
    response = client.post(
        "/api/projects", json=valid_project_payload(name="Western Ghats"), headers=auth_headers(manager)
    )

    assert response.status_code == status.HTTP_201_CREATED
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.CREATED
    assert entry.entity_type == "project"
    assert entry.entity_id == response.json()["id"]
    assert entry.project_id == response.json()["id"]
    assert entry.user_id == manager.id
    assert entry.details == {"name": "Western Ghats"}


def test_updating_a_project_records_only_the_fields_that_changed(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    response = client.patch(
        f"/api/projects/{project.id}",
        # "unit" is sent with its current value, so it is not a change.
        json={"status": "completed", "target_value": 1200, "unit": "trees", "end_date": "2027-03-31"},
        headers=auth_headers(manager),
    )

    assert response.status_code == status.HTTP_200_OK
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.UPDATED
    assert entry.entity_id == project.id
    assert entry.project_id == project.id
    assert entry.details == {
        "name": "Western Ghats",
        "changes": {
            "status": {"from": "active", "to": "completed"},
            "target_value": {"from": 1000, "to": 1200},
            "end_date": {"from": "2026-12-31", "to": "2027-03-31"},
        },
    }


def test_renaming_records_the_new_name_and_the_change(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    client.patch(f"/api/projects/{project.id}", json={"name": "Ghats Revival"}, headers=auth_headers(manager))

    [entry] = activity_rows(db_session)
    assert entry.details == {
        "name": "Ghats Revival",
        "changes": {"name": {"from": "Western Ghats", "to": "Ghats Revival"}},
    }


def test_budget_change_is_stored_as_a_json_number(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    client.patch(f"/api/projects/{project.id}", json={"budget_inr": 250000.5}, headers=auth_headers(manager))

    [entry] = activity_rows(db_session)
    assert entry.details["changes"] == {"budget_inr": {"from": None, "to": 250000.5}}


def test_deleting_a_project_records_one_deleted_entry_with_its_name(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    project_id = project.id

    response = client.delete(f"/api/projects/{project_id}", headers=auth_headers(manager))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.DELETED
    assert entry.entity_type == "project"
    assert entry.entity_id == project_id
    assert entry.details == {"name": "Western Ghats"}


def test_logging_progress_records_from_to_and_correction_flag(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    first = log(client, manager, project.id, value=600)
    second = log(client, manager, project.id, value=850)

    assert first.status_code == second.status_code == status.HTTP_201_CREATED
    entries = activity_rows(db_session)
    assert [entry.action for entry in entries] == [ActivityAction.PROGRESS_LOGGED] * 2
    assert entries[1].entity_type == "progress_update"
    assert entries[1].entity_id == second.json()["id"]
    assert entries[1].project_id == project.id
    assert entries[0].details == {"from": 0, "to": 600, "is_correction": False}
    assert entries[1].details == {"from": 600, "to": 850, "is_correction": False}


def test_a_correction_is_flagged_in_the_entry(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=850)

    log(client, manager, project.id, value=800, is_correction=True, note="Recount found 50 dead saplings.")

    assert activity_rows(db_session)[-1].details == {"from": 850, "to": 800, "is_correction": True}


def test_undoing_progress_records_one_progress_deleted_entry(
    client: TestClient, db_session: Session, create_user: CreateUser, manager: User, project: Project
) -> None:
    admin = create_user(role=UserRole.ADMIN, name="Asha Admin")
    log(client, manager, project.id, value=600)
    update_id = log(client, manager, project.id, value=850).json()["id"]

    response = client.delete(f"/api/projects/{project.id}/progress/{update_id}", headers=auth_headers(admin))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    entry = activity_rows(db_session)[-1]
    assert activity_count(db_session) == 3
    assert entry.action == ActivityAction.PROGRESS_DELETED
    assert entry.user_id == admin.id
    assert entry.entity_type == "progress_update"
    assert entry.entity_id == update_id
    assert entry.project_id == project.id
    assert entry.details == {"from": 600, "to": 850}


# ---------- no-op and rejected requests write nothing ----------


def test_update_that_changes_nothing_records_nothing(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    response = client.patch(
        f"/api/projects/{project.id}",
        json={"name": "Western Ghats", "target_value": 1000, "status": "active"},
        headers=auth_headers(manager),
    )

    assert response.status_code == status.HTTP_200_OK
    assert activity_count(db_session) == 0


def test_empty_update_records_nothing(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    client.patch(f"/api/projects/{project.id}", json={}, headers=auth_headers(manager))

    assert activity_count(db_session) == 0


def test_rejected_decrease_without_a_note_records_nothing(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=850)

    response = log(client, manager, project.id, value=700)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROGRESS_DECREASE_REQUIRES_NOTE"
    assert activity_count(db_session) == 1  # only the accepted 850


def test_non_owner_rejected_requests_record_nothing(
    client: TestClient, db_session: Session, create_user: CreateUser, project: Project
) -> None:
    other_manager = create_user(role=UserRole.MANAGER)

    responses = [
        client.patch(
            f"/api/projects/{project.id}", json={"name": "Taken"}, headers=auth_headers(other_manager)
        ),
        log(client, other_manager, project.id, value=600),
        client.delete(f"/api/projects/{project.id}", headers=auth_headers(other_manager)),
    ]

    assert [response.status_code for response in responses] == [status.HTTP_403_FORBIDDEN] * 3
    assert activity_count(db_session) == 0


def test_viewer_cannot_create_and_nothing_is_recorded(
    client: TestClient, db_session: Session, create_user: CreateUser
) -> None:
    viewer = create_user(role=UserRole.VIEWER)

    response = client.post("/api/projects", json=valid_project_payload(), headers=auth_headers(viewer))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert activity_count(db_session) == 0


def test_invalid_payloads_record_nothing(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    responses = [
        client.post(
            "/api/projects", json=valid_project_payload(target_value=-5), headers=auth_headers(manager)
        ),
        client.patch(
            f"/api/projects/{project.id}", json={"end_date": "2025-01-01"}, headers=auth_headers(manager)
        ),
        log(client, manager, project.id, value=-5),
    ]

    assert [response.status_code for response in responses] == [status.HTTP_422_UNPROCESSABLE_CONTENT] * 3
    assert activity_count(db_session) == 0


# ---------- history survives project deletion ----------


def test_entries_survive_project_deletion_with_project_id_cleared(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    project_id = project.id
    client.patch(f"/api/projects/{project_id}", json={"status": "on_hold"}, headers=auth_headers(manager))
    client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=auth_headers(manager))
    log(client, manager, project_id, value=600)

    client.delete(f"/api/projects/{project_id}", headers=auth_headers(manager))
    db_session.expire_all()

    entries = activity_rows(db_session)
    assert [entry.action for entry in entries] == [
        ActivityAction.UPDATED,
        ActivityAction.UPDATED,
        ActivityAction.PROGRESS_LOGGED,
        ActivityAction.DELETED,
    ]
    assert all(entry.project_id is None for entry in entries)
    assert entries[-1].details["name"] == "Western Ghats"


def test_api_still_names_a_deleted_project(client: TestClient, manager: User, project: Project) -> None:
    project_id = project.id
    log(client, manager, project_id, value=600)
    client.delete(f"/api/projects/{project_id}", headers=auth_headers(manager))

    deleted_entry, progress_entry = read_activity(client, manager).json()

    assert deleted_entry["action"] == "deleted"
    assert deleted_entry["project_id"] is None
    assert deleted_entry["project_name"] == "Western Ghats"
    assert deleted_entry["summary"] == "Field Manager deleted project Western Ghats"
    # Progress details carry no name (ARCHITECTURE.md 7.5), so the summary says the project is gone.
    assert progress_entry["project_name"] is None
    assert progress_entry["summary"] == "Field Manager logged progress on a deleted project: 0 → 600"


# ---------- GET /activity ----------


def test_activity_requires_login(client: TestClient) -> None:
    response = client.get(ACTIVITY_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_viewer_can_read_activity(
    client: TestClient, create_user: CreateUser, manager: User, project: Project
) -> None:
    viewer = create_user(role=UserRole.VIEWER)
    log(client, manager, project.id, value=600)

    response = read_activity(client, viewer)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_activity_item_has_every_field_and_a_summary(
    client: TestClient, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=600)
    update_id = log(client, manager, project.id, value=850).json()["id"]

    item = read_activity(client, manager).json()[0]

    assert item["action"] == "progress_logged"
    assert item["entity_type"] == "progress_update"
    assert item["entity_id"] == update_id
    assert item["project_id"] == project.id
    assert item["project_name"] == "Western Ghats"
    assert item["user_id"] == manager.id
    assert item["user_name"] == "Field Manager"
    assert item["created_at"]
    assert item["details"] == {"from": 600, "to": 850, "is_correction": False}
    assert item["summary"] == "Field Manager logged progress on Western Ghats: 600 → 850"


def test_activity_is_newest_first(client: TestClient, manager: User, project: Project) -> None:
    log(client, manager, project.id, value=100)
    log(client, manager, project.id, value=200)
    log(client, manager, project.id, value=300)

    items = read_activity(client, manager).json()

    assert [item["details"]["to"] for item in items] == [300, 200, 100]
    assert [item["id"] for item in items] == sorted((item["id"] for item in items), reverse=True)


def test_activity_can_be_filtered_by_project(
    client: TestClient, create_project: CreateProject, manager: User, project: Project
) -> None:
    other = create_project(manager, name="Solar Rooftops")
    log(client, manager, project.id, value=600)
    log(client, manager, other.id, value=100)

    items = read_activity(client, manager, f"?project_id={project.id}").json()

    assert [item["project_id"] for item in items] == [project.id]


def test_activity_for_unknown_project_is_404(client: TestClient, manager: User) -> None:
    response = read_activity(client, manager, f"?project_id={MISSING_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "PROJECT_NOT_FOUND"


def test_activity_limit_above_maximum_is_422(client: TestClient, manager: User) -> None:
    response = read_activity(client, manager, f"?limit={ACTIVITY_MAX_LIMIT + 1}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("bad_limit", ["0", "abc"])
def test_activity_limit_must_be_a_positive_number(client: TestClient, manager: User, bad_limit: str) -> None:
    response = read_activity(client, manager, f"?limit={bad_limit}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_activity_limit_caps_the_number_of_items(client: TestClient, manager: User, project: Project) -> None:
    for value in (100, 200, 300):
        log(client, manager, project.id, value=value)

    items = read_activity(client, manager, "?limit=2").json()

    assert [item["details"]["to"] for item in items] == [300, 200]


def test_activity_default_limit_is_50(
    client: TestClient, db_session: Session, manager: User, project: Project
) -> None:
    db_session.add_all(
        ActivityLog(
            user_id=manager.id,
            project_id=project.id,
            action=ActivityAction.CREATED,
            entity_type="project",
            entity_id=project.id,
            details={"name": project.name},
        )
        for _ in range(ACTIVITY_DEFAULT_LIMIT + 5)
    )
    db_session.commit()

    assert len(read_activity(client, manager).json()) == ACTIVITY_DEFAULT_LIMIT


# ---------- summaries ----------


@pytest.mark.parametrize(
    ("action", "details", "expected"),
    [
        (ActivityAction.CREATED, {"name": "Western Ghats"}, "Field Manager created project Western Ghats"),
        (
            ActivityAction.UPDATED,
            {"name": "Western Ghats", "changes": {"status": {}, "target_value": {}}},
            "Field Manager updated Western Ghats: status, target",
        ),
        (ActivityAction.DELETED, {"name": "Western Ghats"}, "Field Manager deleted project Western Ghats"),
        (
            ActivityAction.PROGRESS_LOGGED,
            {"from": 850, "to": 800, "is_correction": True},
            "Field Manager logged progress on Western Ghats: 850 → 800 (correction)",
        ),
        (
            ActivityAction.PROGRESS_DELETED,
            {"from": 600, "to": 850},
            "Field Manager undid the progress entry 600 → 850 on Western Ghats",
        ),
        (
            ActivityAction.ROLE_CHANGED,
            {"email": "ravi@vanatrack.demo", "from": "viewer", "to": "manager"},
            "Field Manager changed ravi@vanatrack.demo's role from viewer to manager",
        ),
        (
            ActivityAction.USER_DEACTIVATED,
            {"email": "ravi@vanatrack.demo"},
            "Field Manager deactivated ravi@vanatrack.demo",
        ),
        (
            ActivityAction.USER_ACTIVATED,
            {"email": "ravi@vanatrack.demo"},
            "Field Manager reactivated ravi@vanatrack.demo",
        ),
    ],
)
def test_every_action_has_a_summary(action: ActivityAction, details: dict, expected: str) -> None:
    assert build_summary(action, "Field Manager", "Western Ghats", details) == expected


def test_every_action_in_the_enum_has_a_summary_builder() -> None:
    """A new action added to the enum without a summary would crash the feed; catch it here."""
    assert set(SUMMARY_BUILDERS) == set(ActivityAction)


# ---------- schema (DATABASE.md 3.4 and 3.5) ----------


def test_activity_foreign_keys_follow_the_deletion_policy(db_session: Session) -> None:
    rules = dict(
        db_session.execute(
            text(
                "SELECT conname, confdeltype FROM pg_constraint "
                "WHERE contype = 'f' AND conrelid = 'activity_logs'::regclass"
            )
        ).all()
    )

    # PostgreSQL codes: r = RESTRICT, n = SET NULL.
    assert rules == {"fk_activity_logs_user_id_users": "r", "fk_activity_logs_project_id_projects": "n"}


def test_activity_table_has_the_three_documented_indexes(db_session: Session) -> None:
    indexes = set(
        db_session.scalars(text("SELECT indexname FROM pg_indexes WHERE tablename = 'activity_logs'"))
    )

    assert {"ix_activity_logs_created", "ix_activity_logs_project", "ix_activity_logs_user"} <= indexes
