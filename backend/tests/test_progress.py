"""Tests for progress tracking: the brief's 600 -> 850 scenario and every rule around it."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.progress_update import ProgressUpdate
from app.models.project import Project, ProjectStatus
from app.models.user import User, UserRole
from app.services import project_service
from tests.conftest import CreateProject, CreateUser, auth_headers

MISSING_ID = 999_999


def progress_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/progress"


def log(client: TestClient, user: User, project_id: int, **body: object):
    return client.post(progress_url(project_id), json=body, headers=auth_headers(user))


def get_project(client: TestClient, user: User, project_id: int) -> dict:
    return client.get(f"/api/projects/{project_id}", headers=auth_headers(user)).json()


@pytest.fixture
def manager(create_user: CreateUser) -> User:
    return create_user(role=UserRole.MANAGER, name="Ravi Kumar")


@pytest.fixture
def project(create_project: CreateProject, manager: User) -> Project:
    """The brief's project: a target of 1,000 trees."""
    return create_project(manager, name="Brief Grove", target_value=1000, unit="trees")


# ---------- the brief's scenario (names from PROMPTS.md) ----------


def test_log_600_then_850_updates_current_value_and_percent(
    client: TestClient, manager: User, project: Project
) -> None:
    assert log(client, manager, project.id, value=600).status_code == status.HTTP_201_CREATED
    assert get_project(client, manager, project.id)["progress_percent"] == 60.0

    response = log(client, manager, project.id, value=850)

    body = get_project(client, manager, project.id)
    assert response.status_code == status.HTTP_201_CREATED
    assert body["current_value"] == 850
    assert body["progress_percent"] == 85.0
    assert body["last_updated_at"] is not None


def test_previous_value_is_recorded_automatically(
    client: TestClient, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=600)

    # A previous_value sent by the client is ignored: the server always works it out.
    body = log(client, manager, project.id, value=850, previous_value=1).json()

    assert body["previous_value"] == 600
    assert body["change"] == 250


def test_decrease_without_correction_returns_400(client: TestClient, manager: User, project: Project) -> None:
    log(client, manager, project.id, value=850)

    response = log(client, manager, project.id, value=700)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROGRESS_DECREASE_REQUIRES_NOTE"
    assert get_project(client, manager, project.id)["current_value"] == 850  # unchanged


def test_decrease_with_correction_and_note_succeeds(
    client: TestClient, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=850)

    response = log(
        client, manager, project.id, value=700, is_correction=True, note="50 saplings died, recount"
    )

    body = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert (body["previous_value"], body["value"], body["change"]) == (850, 700, -150)
    assert body["is_correction"] is True
    assert get_project(client, manager, project.id)["progress_percent"] == 70.0


def test_same_value_returns_400(client: TestClient, manager: User, project: Project) -> None:
    log(client, manager, project.id, value=600)

    response = log(client, manager, project.id, value=600)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROGRESS_NO_CHANGE"


def test_first_update_of_zero_is_no_change(client: TestClient, manager: User, project: Project) -> None:
    assert log(client, manager, project.id, value=0).json()["code"] == "PROGRESS_NO_CHANGE"


def test_negative_value_returns_422(client: TestClient, manager: User, project: Project) -> None:
    response = log(client, manager, project.id, value=-5)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "value" in response.json()["fields"]


@pytest.mark.parametrize("bad_value", [12.5, "850", None, 2_000_000_001])
def test_non_whole_or_too_large_value_returns_422(
    client: TestClient, manager: User, project: Project, bad_value: object
) -> None:
    response = log(client, manager, project.id, value=bad_value)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "value" in response.json()["fields"]


def test_future_recorded_at_returns_422(client: TestClient, manager: User, project: Project) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = log(client, manager, project.id, value=600, recorded_at=tomorrow)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["fields"]["recorded_at"] == "The date cannot be in the future."


def test_recorded_at_without_timezone_returns_422(
    client: TestClient, manager: User, project: Project
) -> None:
    response = log(client, manager, project.id, value=600, recorded_at="2026-06-01T10:00:00")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "recorded_at" in response.json()["fields"]


def test_value_above_target_allowed_and_percent_over_100(
    client: TestClient, manager: User, project: Project
) -> None:
    response = log(client, manager, project.id, value=1120)

    body = get_project(client, manager, project.id)
    assert response.status_code == status.HTTP_201_CREATED
    assert body["progress_percent"] == 112.0
    assert body["is_target_exceeded"] is True


def test_unrealistic_value_returns_400(client: TestClient, manager: User, project: Project) -> None:
    response = log(client, manager, project.id, value=10_001)  # more than 10 x 1,000

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROGRESS_UNREALISTIC"


def test_exactly_ten_times_target_is_allowed(client: TestClient, manager: User, project: Project) -> None:
    assert log(client, manager, project.id, value=10_000).status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize("closed_status", [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED])
def test_log_on_completed_project_returns_400(
    client: TestClient, manager: User, create_project: CreateProject, closed_status: ProjectStatus
) -> None:
    closed = create_project(manager, status=closed_status)

    response = log(client, manager, closed.id, value=100)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROJECT_CLOSED"


@pytest.mark.parametrize("open_status", [ProjectStatus.PLANNED, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD])
def test_log_on_open_project_is_allowed(
    client: TestClient, manager: User, create_project: CreateProject, open_status: ProjectStatus
) -> None:
    open_project = create_project(manager, status=open_status)
    assert log(client, manager, open_project.id, value=100).status_code == status.HTTP_201_CREATED


def test_non_owner_manager_gets_403(
    client: TestClient, create_user: CreateUser, project: Project, db_session: Session
) -> None:
    other_manager = create_user(role=UserRole.MANAGER)

    response = log(client, other_manager, project.id, value=600)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "You can only modify projects you own.", "code": "NOT_PROJECT_OWNER"}
    assert db_session.scalar(select(func.count()).select_from(ProgressUpdate)) == 0


def test_viewer_gets_403(client: TestClient, create_user: CreateUser, project: Project) -> None:
    viewer = create_user(role=UserRole.VIEWER)
    assert log(client, viewer, project.id, value=600).status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_log_on_any_project(client: TestClient, create_user: CreateUser, project: Project) -> None:
    admin = create_user(role=UserRole.ADMIN, name="Head Office")

    response = log(client, admin, project.id, value=600)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["author"]["name"] == "Head Office"


def test_only_admin_can_delete_update(
    client: TestClient, create_user: CreateUser, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=600)
    latest_id = log(client, manager, project.id, value=850).json()["id"]
    admin = create_user(role=UserRole.ADMIN)
    viewer = create_user(role=UserRole.VIEWER)
    delete_url = f"{progress_url(project.id)}/{latest_id}"

    assert client.delete(delete_url, headers=auth_headers(manager)).status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(delete_url, headers=auth_headers(viewer)).status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(delete_url, headers=auth_headers(admin)).status_code == status.HTTP_204_NO_CONTENT
    assert get_project(client, manager, project.id)["current_value"] == 600  # back to the previous total


def test_project_list_and_detail_show_same_current_value(
    client: TestClient, manager: User, project: Project, create_project: CreateProject
) -> None:
    other = create_project(manager, name="Other Grove", target_value=200)
    log(client, manager, project.id, value=600)
    log(client, manager, project.id, value=850)
    log(client, manager, other.id, value=50)

    listed = {p["id"]: p for p in client.get("/api/projects", headers=auth_headers(manager)).json()}

    for project_id in (project.id, other.id):
        detail = get_project(client, manager, project_id)
        assert listed[project_id]["current_value"] == detail["current_value"]
        assert listed[project_id]["progress_percent"] == detail["progress_percent"]
    assert listed[project.id]["current_value"] == 850
    assert listed[other.id]["progress_percent"] == 25.0


# ---------- corrections and notes ----------


@pytest.mark.parametrize("note", [None, "", "too short", "         x"])
def test_correction_without_a_real_note_returns_422(
    client: TestClient, manager: User, project: Project, note: str | None
) -> None:
    log(client, manager, project.id, value=850)

    response = log(client, manager, project.id, value=700, is_correction=True, note=note)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["fields"] == {"note": "Explain the correction in at least 10 characters."}


def test_correction_can_also_raise_the_total(client: TestClient, manager: User, project: Project) -> None:
    log(client, manager, project.id, value=600)

    response = log(
        client, manager, project.id, value=640, is_correction=True, note="Missed one plot in recount"
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_database_rejects_a_correction_without_a_note(
    db_session: Session, manager: User, project: Project
) -> None:
    """Second safety net: the CHECK constraint itself (it must treat a missing note as a failure)."""
    with (
        pytest.raises(IntegrityError, match="ck_progress_updates_correction_needs_note"),
        db_session.begin_nested(),
    ):
        db_session.execute(
            text(
                "INSERT INTO progress_updates "
                "(project_id, value, previous_value, is_correction, note, created_by) "
                "VALUES (:project_id, 5, 6, true, NULL, :user_id)"
            ),
            {"project_id": project.id, "user_id": manager.id},
        )


# ---------- date order ----------


def test_recorded_at_before_project_start_returns_422(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    starts_later = create_project(manager, start_date=date(2026, 6, 1))

    response = log(client, manager, starts_later.id, value=10, recorded_at="2026-05-15T12:00:00+05:30")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "before the project start date" in response.json()["fields"]["recorded_at"]


def test_recorded_at_before_latest_update_returns_422(
    client: TestClient, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=600, recorded_at="2026-06-01T12:00:00+05:30")

    response = log(client, manager, project.id, value=850, recorded_at="2026-05-01T12:00:00+05:30")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "before the latest update" in response.json()["fields"]["recorded_at"]


def test_backdated_entries_in_order_are_accepted(client: TestClient, manager: User, project: Project) -> None:
    log(client, manager, project.id, value=200, recorded_at="2026-03-01T12:00:00+05:30")
    response = log(client, manager, project.id, value=450, recorded_at="2026-04-01T12:00:00+05:30")

    assert response.json()["previous_value"] == 200


# ---------- reading the history ----------


def test_history_is_newest_first_with_author_and_change(
    client: TestClient, manager: User, project: Project, create_user: CreateUser
) -> None:
    log(client, manager, project.id, value=600)
    log(client, manager, project.id, value=850)
    viewer = create_user(role=UserRole.VIEWER)

    history = client.get(progress_url(project.id), headers=auth_headers(viewer)).json()

    assert [(entry["previous_value"], entry["value"], entry["change"]) for entry in history] == [
        (600, 850, 250),
        (0, 600, 600),
    ]
    assert history[0]["author"] == {"id": manager.id, "name": "Ravi Kumar"}
    assert all(entry["can_delete"] is False for entry in history)  # viewers can never delete


def test_history_marks_only_newest_entry_deletable_for_admin(
    client: TestClient, manager: User, project: Project, create_user: CreateUser
) -> None:
    log(client, manager, project.id, value=600)
    log(client, manager, project.id, value=850)
    admin = create_user(role=UserRole.ADMIN)

    history = client.get(progress_url(project.id), headers=auth_headers(admin)).json()

    assert [entry["can_delete"] for entry in history] == [True, False]


def test_history_of_project_without_updates_is_empty(
    client: TestClient, manager: User, project: Project
) -> None:
    assert client.get(progress_url(project.id), headers=auth_headers(manager)).json() == []


def test_progress_requires_login(client: TestClient, project: Project) -> None:
    assert client.get(progress_url(project.id)).status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.post(progress_url(project.id), json={"value": 600}).status_code == status.HTTP_401_UNAUTHORIZED
    )


def test_progress_for_missing_project_returns_404(client: TestClient, create_user: CreateUser) -> None:
    admin = create_user(role=UserRole.ADMIN)

    assert client.get(progress_url(MISSING_ID), headers=auth_headers(admin)).status_code == 404
    assert log(client, admin, MISSING_ID, value=600).status_code == 404
    assert client.delete(f"{progress_url(MISSING_ID)}/1", headers=auth_headers(admin)).status_code == 404


def test_there_is_no_edit_endpoint_for_updates(client: TestClient, manager: User, project: Project) -> None:
    update_id = log(client, manager, project.id, value=600).json()["id"]

    response = client.patch(
        f"{progress_url(project.id)}/{update_id}", json={"value": 1}, headers=auth_headers(manager)
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ---------- undoing the latest entry ----------


def test_only_the_newest_update_can_be_deleted(
    client: TestClient, manager: User, project: Project, create_user: CreateUser
) -> None:
    first_id = log(client, manager, project.id, value=600).json()["id"]
    log(client, manager, project.id, value=850)
    admin = create_user(role=UserRole.ADMIN)

    response = client.delete(f"{progress_url(project.id)}/{first_id}", headers=auth_headers(admin))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "PROGRESS_NOT_LATEST"


def test_deleting_an_update_through_another_project_returns_404(
    client: TestClient,
    manager: User,
    project: Project,
    create_project: CreateProject,
    create_user: CreateUser,
) -> None:
    update_id = log(client, manager, project.id, value=600).json()["id"]
    other = create_project(manager, name="Other")
    admin = create_user(role=UserRole.ADMIN)

    response = client.delete(f"{progress_url(other.id)}/{update_id}", headers=auth_headers(admin))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "PROGRESS_UPDATE_NOT_FOUND"


# ---------- derived values elsewhere ----------


def test_lowering_target_below_current_is_allowed_and_flagged(
    client: TestClient, manager: User, project: Project
) -> None:
    log(client, manager, project.id, value=850)

    response = client.patch(
        f"/api/projects/{project.id}", json={"target_value": 800}, headers=auth_headers(manager)
    )

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["is_target_exceeded"] is True
    assert body["progress_percent"] == 106.3


def test_sort_by_progress_uses_real_progress(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    low = create_project(manager, name="Low", target_value=1000)
    high = create_project(manager, name="High", target_value=100)
    create_project(manager, name="None")
    log(client, manager, low.id, value=100)  # 10%
    log(client, manager, high.id, value=90)  # 90%

    response = client.get("/api/projects?sort=progress&order=desc", headers=auth_headers(manager))

    assert [p["name"] for p in response.json()] == ["High", "Low", "None"]


def test_good_progress_is_not_behind_schedule(
    client: TestClient, manager: User, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(project_service, "today_in_app_timezone", lambda: date(2026, 7, 2))  # 50% of timeline
    log(client, manager, project.id, value=450)  # 45%: within 10 points

    assert get_project(client, manager, project.id)["is_behind_schedule"] is False
    log(client, manager, project.id, value=300, is_correction=True, note="Recount after storm damage")  # 30%
    assert get_project(client, manager, project.id)["is_behind_schedule"] is True


# ---------- deletion policy, applied to progress ----------


def test_deleting_a_project_deletes_its_updates(
    client: TestClient, manager: User, project: Project, db_session: Session
) -> None:
    log(client, manager, project.id, value=600)
    log(client, manager, project.id, value=850)

    assert client.delete(f"/api/projects/{project.id}", headers=auth_headers(manager)).status_code == 204
    remaining = db_session.scalar(
        select(func.count()).select_from(ProgressUpdate).where(ProgressUpdate.project_id == project.id)
    )
    assert remaining == 0


def test_user_who_logged_updates_cannot_be_deleted(
    client: TestClient, create_user: CreateUser, project: Project, db_session: Session
) -> None:
    admin = create_user(role=UserRole.ADMIN)
    log(client, admin, project.id, value=600)

    with (
        pytest.raises(IntegrityError, match="fk_progress_updates_created_by_users"),
        db_session.begin_nested(),
    ):
        db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": admin.id})
