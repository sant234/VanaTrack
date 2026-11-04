"""Tests for project create, read, update, delete, permissions and options."""

from datetime import UTC, date, datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import UserRole
from app.services import project_service
from tests.conftest import CreateProject, CreateUser, auth_headers, valid_project_payload

PROJECTS_URL = "/api/projects"
NOT_OWNER_MESSAGE = {"detail": "You can only modify projects you own.", "code": "NOT_PROJECT_OWNER"}
MISSING_PROJECT_ID = 999_999
A_YEAR_AGO = datetime(2025, 11, 1, tzinfo=UTC)


def project_url(project_id: int) -> str:
    return f"{PROJECTS_URL}/{project_id}"


# ---------- create ----------


def test_manager_creates_project_and_becomes_owner(client: TestClient, create_user: CreateUser) -> None:
    manager = create_user(role=UserRole.MANAGER, name="Ravi Kumar")

    response = client.post(PROJECTS_URL, json=valid_project_payload(), headers=auth_headers(manager))

    body = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert body["owner"] == {"id": manager.id, "name": "Ravi Kumar"}
    assert body["can_edit"] is True
    assert body["current_value"] == 0
    assert body["progress_percent"] == 0.0
    assert body["last_updated_at"] is None
    assert body["budget_inr"] == 250000.0


def test_admin_can_create_project(client: TestClient, create_user: CreateUser) -> None:
    admin = create_user(role=UserRole.ADMIN)

    response = client.post(PROJECTS_URL, json=valid_project_payload(), headers=auth_headers(admin))

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["owner"]["id"] == admin.id


def test_viewer_cannot_create_project(client: TestClient, create_user: CreateUser) -> None:
    viewer = create_user(role=UserRole.VIEWER)

    response = client.post(PROJECTS_URL, json=valid_project_payload(), headers=auth_headers(viewer))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "INSUFFICIENT_ROLE"


def test_create_requires_login(client: TestClient) -> None:
    assert client.post(PROJECTS_URL, json=valid_project_payload()).status_code == status.HTTP_401_UNAUTHORIZED


def test_create_cleans_up_text_fields(client: TestClient, create_user: CreateUser) -> None:
    manager = create_user(role=UserRole.MANAGER)
    payload = valid_project_payload(
        name="  Mangrove Belt  ", unit=" Trees ", state="tamil nadu", district="  "
    )

    body = client.post(PROJECTS_URL, json=payload, headers=auth_headers(manager)).json()

    assert body["name"] == "Mangrove Belt"
    assert body["unit"] == "trees"
    assert body["state"] == "Tamil Nadu"
    assert body["district"] is None


def test_create_ignores_owner_id_in_body(client: TestClient, create_user: CreateUser) -> None:
    manager = create_user(role=UserRole.MANAGER)
    someone_else = create_user(role=UserRole.MANAGER)

    response = client.post(
        PROJECTS_URL, json=valid_project_payload(owner_id=someone_else.id), headers=auth_headers(manager)
    )

    assert response.json()["owner"]["id"] == manager.id


@pytest.mark.parametrize(
    ("overrides", "bad_field"),
    [
        ({"target_value": 0}, "target_value"),
        ({"target_value": -5}, "target_value"),
        ({"target_value": 12.5}, "target_value"),
        ({"target_value": "1000"}, "target_value"),
        ({"end_date": "2025-12-31"}, "end_date"),
        ({"type": "forest"}, "type"),
        ({"status": "done"}, "status"),
        ({"name": "ab"}, "name"),
        ({"name": "   "}, "name"),
        ({"state": "Atlantis"}, "state"),
        ({"budget_inr": -1}, "budget_inr"),
        ({"budget_inr": 10.123}, "budget_inr"),
        ({"unit": ""}, "unit"),
        ({"description": "x" * 2001}, "description"),
        ({"start_date": "not-a-date"}, "start_date"),
    ],
)
def test_create_rejects_invalid_input(
    client: TestClient, create_user: CreateUser, overrides: dict, bad_field: str
) -> None:
    manager = create_user(role=UserRole.MANAGER)

    response = client.post(
        PROJECTS_URL, json=valid_project_payload(**overrides), headers=auth_headers(manager)
    )

    body = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert body["code"] == "VALIDATION_ERROR"
    assert bad_field in body["fields"]
    assert not body["fields"][bad_field].startswith("Value error")


def test_create_missing_required_fields_lists_each_one(client: TestClient, create_user: CreateUser) -> None:
    manager = create_user(role=UserRole.MANAGER)

    response = client.post(PROJECTS_URL, json={}, headers=auth_headers(manager))

    expected = {"name", "type", "target_value", "unit", "state", "start_date", "end_date"}
    assert set(response.json()["fields"]) == expected


# ---------- read ----------


def test_anyone_logged_in_can_read_a_project(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER, name="Ravi Kumar")
    viewer = create_user(role=UserRole.VIEWER)
    project = create_project(owner, name="Solar Rooftops")

    response = client.get(project_url(project.id), headers=auth_headers(viewer))

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["name"] == "Solar Rooftops"
    assert body["owner"]["name"] == "Ravi Kumar"
    assert body["can_edit"] is False


def test_read_missing_project_returns_404(client: TestClient, create_user: CreateUser) -> None:
    viewer = create_user()

    response = client.get(project_url(MISSING_PROJECT_ID), headers=auth_headers(viewer))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Project not found.", "code": "PROJECT_NOT_FOUND"}


def test_read_requires_login(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    assert client.get(project_url(project.id)).status_code == status.HTTP_401_UNAUTHORIZED


def test_expected_percent_uses_todays_date(
    client: TestClient,
    create_user: CreateUser,
    create_project: CreateProject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_service, "today_in_app_timezone", lambda: date(2026, 7, 2))
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    body = client.get(project_url(project.id), headers=auth_headers(owner)).json()

    assert body["expected_percent"] == 50.0
    assert body["is_behind_schedule"] is True  # active, 0% done vs 50% expected


# ---------- update ----------


def test_owner_can_update_project(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, db_session: Session
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner, name="Old Name")
    # Each test is one database transaction, where now() never changes, so make the row look old first.
    project.updated_at = A_YEAR_AGO
    db_session.commit()

    response = client.patch(
        project_url(project.id), json={"name": "New Name", "status": "on_hold"}, headers=auth_headers(owner)
    )

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["name"] == "New Name"
    assert body["status"] == "on_hold"
    assert body["unit"] == "trees"  # fields that were not sent stay as they were
    db_session.refresh(project)
    assert project.updated_at > A_YEAR_AGO


def test_admin_can_update_any_project(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    admin = create_user(role=UserRole.ADMIN)

    response = client.patch(project_url(project.id), json={"target_value": 2000}, headers=auth_headers(admin))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["target_value"] == 2000


def test_other_manager_cannot_update(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    other_manager = create_user(role=UserRole.MANAGER)

    response = client.patch(
        project_url(project.id), json={"name": "Hijacked"}, headers=auth_headers(other_manager)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == NOT_OWNER_MESSAGE


def test_viewer_cannot_update(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    viewer = create_user(role=UserRole.VIEWER)

    response = client.patch(project_url(project.id), json={"name": "Nope"}, headers=auth_headers(viewer))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_missing_project_returns_404(client: TestClient, create_user: CreateUser) -> None:
    admin = create_user(role=UserRole.ADMIN)

    response = client.patch(
        project_url(MISSING_PROJECT_ID), json={"name": "Ghost"}, headers=auth_headers(admin)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_end_date_before_saved_start_date_is_rejected(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    response = client.patch(
        project_url(project.id), json={"end_date": "2025-06-30"}, headers=auth_headers(owner)
    )

    body = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert body["fields"] == {"end_date": "End date cannot be before the start date."}


def test_update_start_date_after_saved_end_date_is_rejected(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    response = client.patch(
        project_url(project.id), json={"start_date": "2027-02-01"}, headers=auth_headers(owner)
    )

    assert response.json()["fields"] == {"start_date": "Start date cannot be after the end date."}


def test_update_cannot_clear_required_field(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner)

    response = client.patch(project_url(project.id), json={"name": None}, headers=auth_headers(owner))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["fields"]["name"] == "This field cannot be empty."


def test_update_can_clear_optional_field(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner, district="Mysuru")

    response = client.patch(project_url(project.id), json={"district": None}, headers=auth_headers(owner))

    assert response.json()["district"] is None


def test_update_cannot_change_owner(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner)
    other = create_user(role=UserRole.MANAGER)

    response = client.patch(project_url(project.id), json={"owner_id": other.id}, headers=auth_headers(owner))

    assert response.json()["owner"]["id"] == owner.id


# ---------- delete ----------


def test_owner_can_delete_project(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner)

    response = client.delete(project_url(project.id), headers=auth_headers(owner))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert client.get(project_url(project.id), headers=auth_headers(owner)).status_code == 404


def test_admin_can_delete_any_project(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, db_session: Session
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    admin = create_user(role=UserRole.ADMIN)

    assert client.delete(project_url(project.id), headers=auth_headers(admin)).status_code == 204
    assert db_session.get(Project, project.id) is None


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.VIEWER])
def test_non_owner_cannot_delete(
    client: TestClient,
    create_user: CreateUser,
    create_project: CreateProject,
    db_session: Session,
    role: UserRole,
) -> None:
    project = create_project(create_user(role=UserRole.MANAGER))
    intruder = create_user(role=role)

    response = client.delete(project_url(project.id), headers=auth_headers(intruder))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert db_session.get(Project, project.id) is not None


def test_delete_missing_project_returns_404(client: TestClient, create_user: CreateUser) -> None:
    admin = create_user(role=UserRole.ADMIN)
    assert client.delete(project_url(MISSING_PROJECT_ID), headers=auth_headers(admin)).status_code == 404


# ---------- can_edit ----------


def test_can_edit_flag_matches_permissions(
    client: TestClient, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner)
    viewers_and_expected = [
        (owner, True),
        (create_user(role=UserRole.ADMIN), True),
        (create_user(role=UserRole.MANAGER), False),
        (create_user(role=UserRole.VIEWER), False),
    ]

    for user, expected in viewers_and_expected:
        body = client.get(project_url(project.id), headers=auth_headers(user)).json()
        assert body["can_edit"] is expected, f"{user.role} should have can_edit={expected}"


def test_owner_demoted_to_viewer_loses_edit_rights(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, db_session: Session
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    project = create_project(owner)
    owner.role = UserRole.VIEWER
    db_session.commit()

    assert client.get(project_url(project.id), headers=auth_headers(owner)).json()["can_edit"] is False
    response = client.patch(
        project_url(project.id), json={"name": "Still mine?"}, headers=auth_headers(owner)
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------- options ----------


def test_options_returns_dropdown_choices(client: TestClient, create_user: CreateUser) -> None:
    body = client.get(f"{PROJECTS_URL}/options", headers=auth_headers(create_user())).json()

    assert {"value": "water_conservation", "label": "Water conservation"} in body["types"]
    assert [option["value"] for option in body["statuses"]] == [
        "planned",
        "active",
        "on_hold",
        "completed",
        "cancelled",
    ]
    assert "Karnataka" in body["states"]
    assert len(body["states"]) == 36  # 28 states + 8 union territories


def test_options_requires_login(client: TestClient) -> None:
    assert client.get(f"{PROJECTS_URL}/options").status_code == status.HTTP_401_UNAUTHORIZED
