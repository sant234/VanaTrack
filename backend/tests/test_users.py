"""Tests for user management: admin-only access, self-protection, activity entries, and token effects."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.user import User, UserRole
from tests.conftest import CreateProject, CreateUser, auth_headers, valid_project_payload

MISSING_ID = 999_999
USERS_URL = "/api/users"


@pytest.fixture
def admin(create_user: CreateUser) -> User:
    return create_user(role=UserRole.ADMIN, name="Asha Admin", email="asha@vanatrack.demo")


@pytest.fixture
def viewer(create_user: CreateUser) -> User:
    return create_user(role=UserRole.VIEWER, name="Vikram Viewer", email="vikram@vanatrack.demo")


def patch_user(client: TestClient, actor: User, user_id: int, body: dict):
    return client.patch(f"{USERS_URL}/{user_id}", json=body, headers=auth_headers(actor))


def activity_rows(db_session: Session) -> list[ActivityLog]:
    return list(db_session.scalars(select(ActivityLog).order_by(ActivityLog.id)))


def activity_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(ActivityLog))


# ---------- access ----------


def test_users_endpoints_require_login(client: TestClient, viewer: User) -> None:
    assert client.get(USERS_URL).status_code == status.HTTP_401_UNAUTHORIZED
    response = client.patch(f"{USERS_URL}/{viewer.id}", json={"role": "manager"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.VIEWER])
def test_non_admin_gets_403_on_both_endpoints(
    client: TestClient, db_session: Session, create_user: CreateUser, viewer: User, role: UserRole
) -> None:
    caller = create_user(role=role)

    list_response = client.get(USERS_URL, headers=auth_headers(caller))
    patch_response = patch_user(client, caller, viewer.id, {"role": "admin"})

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert patch_response.status_code == status.HTTP_403_FORBIDDEN
    assert patch_response.json()["code"] == "INSUFFICIENT_ROLE"
    db_session.refresh(viewer)
    assert viewer.role == UserRole.VIEWER
    assert activity_count(db_session) == 0


def test_unknown_user_is_404(client: TestClient, admin: User) -> None:
    response = patch_user(client, admin, MISSING_ID, {"role": "manager"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "USER_NOT_FOUND"


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"role": "superuser"}, "role"),
        ({"role": None}, "role"),
        ({"is_active": "yes"}, "is_active"),
        ({"is_active": None}, "is_active"),
    ],
)
def test_invalid_values_are_422(
    client: TestClient, db_session: Session, admin: User, viewer: User, body: dict, field: str
) -> None:
    response = patch_user(client, admin, viewer.id, body)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert field in response.json()["fields"]
    assert activity_count(db_session) == 0


# ---------- list ----------


def test_admin_lists_users_sorted_by_name_with_project_counts(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, admin: User, viewer: User
) -> None:
    manager = create_user(role=UserRole.MANAGER, name="Meera Manager")
    create_project(manager)
    create_project(manager)

    response = client.get(USERS_URL, headers=auth_headers(admin))

    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    assert [user["name"] for user in users] == ["Asha Admin", "Meera Manager", "Vikram Viewer"]
    meera = users[1]
    assert set(meera) == {"id", "name", "email", "role", "is_active", "created_at", "owned_project_count"}
    assert meera["role"] == "manager"
    assert meera["is_active"] is True
    assert meera["owned_project_count"] == 2
    assert users[0]["owned_project_count"] == 0


# ---------- role changes ----------


def test_admin_promotes_viewer_to_manager(
    client: TestClient, db_session: Session, admin: User, viewer: User
) -> None:
    response = patch_user(client, admin, viewer.id, {"role": "manager"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "manager"
    assert response.json()["owned_project_count"] == 0
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.ROLE_CHANGED
    assert entry.user_id == admin.id
    assert entry.entity_type == "user"
    assert entry.entity_id == viewer.id
    assert entry.project_id is None
    assert entry.details == {"email": "vikram@vanatrack.demo", "from": "viewer", "to": "manager"}


def test_promoted_manager_can_create_a_project_with_the_same_token(
    client: TestClient, admin: User, viewer: User
) -> None:
    """The role is re-read from the database on every request, so the old token gains the new rights."""
    viewer_headers = auth_headers(viewer)
    before = client.post("/api/projects", json=valid_project_payload(), headers=viewer_headers)

    patch_user(client, admin, viewer.id, {"role": "manager"})
    after = client.post("/api/projects", json=valid_project_payload(), headers=viewer_headers)

    assert before.status_code == status.HTTP_403_FORBIDDEN
    assert after.status_code == status.HTTP_201_CREATED
    assert after.json()["owner"]["id"] == viewer.id


def test_admin_cannot_change_own_role(client: TestClient, db_session: Session, admin: User) -> None:
    response = patch_user(client, admin, admin.id, {"role": "manager"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "CANNOT_MODIFY_SELF"
    assert "your own role" in response.json()["detail"]
    db_session.refresh(admin)
    assert admin.role == UserRole.ADMIN
    assert activity_count(db_session) == 0


def test_admin_cannot_deactivate_self(client: TestClient, db_session: Session, admin: User) -> None:
    response = patch_user(client, admin, admin.id, {"is_active": False})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "CANNOT_MODIFY_SELF"
    assert "deactivate your own account" in response.json()["detail"]
    db_session.refresh(admin)
    assert admin.is_active is True
    assert activity_count(db_session) == 0


def test_admin_sending_own_current_values_is_a_no_op(
    client: TestClient, db_session: Session, admin: User
) -> None:
    response = patch_user(client, admin, admin.id, {"role": "admin", "is_active": True})

    assert response.status_code == status.HTTP_200_OK
    assert activity_count(db_session) == 0


def test_admin_can_demote_another_admin(
    client: TestClient, db_session: Session, create_user: CreateUser, admin: User
) -> None:
    other_admin = create_user(role=UserRole.ADMIN, email="second.admin@vanatrack.demo")

    response = patch_user(client, admin, other_admin.id, {"role": "viewer"})

    assert response.status_code == status.HTTP_200_OK
    assert activity_rows(db_session)[0].details == {
        "email": "second.admin@vanatrack.demo",
        "from": "admin",
        "to": "viewer",
    }


# ---------- deactivation and reactivation ----------


def test_deactivated_users_existing_token_gets_401(
    client: TestClient, db_session: Session, admin: User, viewer: User
) -> None:
    viewer_headers = auth_headers(viewer)
    assert client.get("/api/auth/me", headers=viewer_headers).status_code == status.HTTP_200_OK

    response = patch_user(client, admin, viewer.id, {"is_active": False})
    next_request = client.get("/api/projects", headers=viewer_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is False
    assert next_request.status_code == status.HTTP_401_UNAUTHORIZED
    assert next_request.json()["code"] == "ACCOUNT_DEACTIVATED"
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.USER_DEACTIVATED
    assert entry.entity_id == viewer.id
    assert entry.details == {"email": "vikram@vanatrack.demo"}


def test_reactivation_restores_access(
    client: TestClient, db_session: Session, create_user: CreateUser, admin: User
) -> None:
    inactive = create_user(role=UserRole.VIEWER, email="inactive@vanatrack.demo", is_active=False)
    inactive_headers = auth_headers(inactive)
    assert client.get("/api/auth/me", headers=inactive_headers).status_code == status.HTTP_401_UNAUTHORIZED

    response = patch_user(client, admin, inactive.id, {"is_active": True})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_active"] is True
    assert client.get("/api/auth/me", headers=inactive_headers).status_code == status.HTTP_200_OK
    [entry] = activity_rows(db_session)
    assert entry.action == ActivityAction.USER_ACTIVATED
    assert entry.details == {"email": "inactive@vanatrack.demo"}


# ---------- activity: exactly one row per real change ----------


def test_changing_role_and_status_together_writes_one_row_each(
    client: TestClient, db_session: Session, admin: User, viewer: User
) -> None:
    response = patch_user(client, admin, viewer.id, {"role": "manager", "is_active": False})

    assert response.status_code == status.HTTP_200_OK
    entries = activity_rows(db_session)
    assert [entry.action for entry in entries] == [
        ActivityAction.ROLE_CHANGED,
        ActivityAction.USER_DEACTIVATED,
    ]
    assert entries[0].details == {"email": "vikram@vanatrack.demo", "from": "viewer", "to": "manager"}
    assert entries[1].details == {"email": "vikram@vanatrack.demo"}


def test_update_with_unchanged_values_writes_nothing(
    client: TestClient, db_session: Session, admin: User, viewer: User
) -> None:
    response = patch_user(client, admin, viewer.id, {"role": "viewer", "is_active": True})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "viewer"
    assert activity_count(db_session) == 0


def test_empty_body_changes_nothing_and_writes_nothing(
    client: TestClient, db_session: Session, admin: User, viewer: User
) -> None:
    response = patch_user(client, admin, viewer.id, {})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "viewer"
    assert response.json()["is_active"] is True
    assert activity_count(db_session) == 0


def test_user_entries_appear_in_the_activity_feed_with_summaries(
    client: TestClient, admin: User, viewer: User
) -> None:
    patch_user(client, admin, viewer.id, {"role": "manager"})
    patch_user(client, admin, viewer.id, {"is_active": False})
    patch_user(client, admin, viewer.id, {"is_active": True})

    feed = client.get("/api/activity", headers=auth_headers(admin)).json()

    assert [item["summary"] for item in feed] == [
        "Asha Admin reactivated vikram@vanatrack.demo",
        "Asha Admin deactivated vikram@vanatrack.demo",
        "Asha Admin changed vikram@vanatrack.demo's role from viewer to manager",
    ]
    assert all(item["project_id"] is None and item["entity_type"] == "user" for item in feed)
