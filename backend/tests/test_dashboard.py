"""Tests for the dashboard endpoints.

"Today" is fixed to 2 Jul 2026 so every expected number is exact: a project running
1 Jan - 31 Dec 2026 is then 50% through its timeline (182 of 364 days).
"""

from datetime import date

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User, UserRole
from app.services import dashboard_service
from tests.conftest import CreateProject, CreateUser, auth_headers

TODAY = date(2026, 7, 2)
DASHBOARD_ENDPOINTS = ["summary", "by-type", "by-state", "trend", "attention"]


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dashboard_service, "today_in_app_timezone", lambda: TODAY)


@pytest.fixture
def manager(create_user: CreateUser) -> User:
    return create_user(role=UserRole.MANAGER, name="Ravi Kumar")


def get(client: TestClient, user: User, endpoint: str, query: str = ""):
    response = client.get(f"/api/dashboard/{endpoint}{query}", headers=auth_headers(user))
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


def log(client: TestClient, user: User, project: Project, value: int, on: str, note: str | None = None):
    """Log a running total on a given day (noon, India time)."""
    body = {"value": value, "recorded_at": f"{on}T12:00:00+05:30"}
    if note:
        body |= {"is_correction": True, "note": note}
    response = client.post(f"/api/projects/{project.id}/progress", json=body, headers=auth_headers(user))
    assert response.status_code == status.HTTP_201_CREATED, response.text


# ---------- named in PROMPTS.md ----------


def test_empty_database_returns_zeros_not_errors(client: TestClient, create_user: CreateUser) -> None:
    viewer = create_user(role=UserRole.VIEWER)

    summary = get(client, viewer, "summary")

    assert summary["total_projects"] == 0
    assert summary["average_completion_percent"] == 0.0
    assert summary["trees_planted"] == 0
    assert summary["estimated_co2_tonnes_per_year"] == 0.0
    assert summary["behind_schedule_count"] == 0
    assert get(client, viewer, "by-type") == []
    assert get(client, viewer, "by-state") == []
    assert get(client, viewer, "attention") == []
    trend = get(client, viewer, "trend")
    assert len(trend) == 12
    assert all(point["average_completion_percent"] is None for point in trend)


def test_600_then_850_counts_850_not_1450(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove = create_project(manager, name="Brief Grove", target_value=1000, unit="trees")
    log(client, manager, grove, 600, "2026-05-01")
    log(client, manager, grove, 850, "2026-06-01")

    summary = get(client, manager, "summary")

    assert summary["trees_planted"] == 850
    assert summary["average_completion_percent"] == 85.0
    assert summary["estimated_co2_tonnes_per_year"] == round(850 * 21 / 1000, 1)


def test_correction_reduces_totals(client: TestClient, manager: User, create_project: CreateProject) -> None:
    grove = create_project(manager, target_value=1000, unit="trees")
    log(client, manager, grove, 850, "2026-05-01")
    log(client, manager, grove, 700, "2026-06-01", note="50 saplings died, recount")

    summary = get(client, manager, "summary")

    assert summary["trees_planted"] == 700
    assert summary["average_completion_percent"] == 70.0


def test_behind_schedule_and_attention_with_controlled_dates(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    # Today is 2 Jul: every project below runs 1 Jan - 31 Dec, so 50% of the timeline has passed.
    behind = create_project(manager, name="Behind", target_value=100)  # 30%: more than 10 points behind
    on_track = create_project(manager, name="On track", target_value=100)  # 45%: within 10 points
    paused = create_project(manager, name="Paused", status=ProjectStatus.ON_HOLD)  # not judged
    stale = create_project(manager, name="Stale", target_value=100)  # 60%, but last update 40 days ago
    new_start = create_project(manager, name="New", start_date=date(2026, 6, 25))  # started 7 days ago
    never_logged = create_project(manager, name="Never logged", start_date=date(2026, 5, 1))
    log(client, manager, behind, 30, "2026-06-30")
    log(client, manager, on_track, 45, "2026-06-30")
    log(client, manager, stale, 60, "2026-05-23")

    summary = get(client, manager, "summary")
    attention = {item["name"]: item for item in get(client, manager, "attention")}

    assert summary["behind_schedule_count"] == 2  # "Behind", and "Never logged" (0% vs 34.8% expected)
    assert set(attention) == {"Behind", "Stale", "Never logged"}
    assert attention["Behind"]["reasons"] == ["behind_schedule"]
    assert attention["Stale"]["reasons"] == ["no_recent_update"]
    assert attention["Stale"]["days_since_update"] == 40
    assert attention["Never logged"]["reasons"] == ["behind_schedule", "no_recent_update"]
    assert attention["Never logged"]["days_since_update"] is None
    assert attention["Never logged"]["id"] == never_logged.id
    assert summary["needs_attention_count"] == 3
    assert {on_track.name, paused.name, new_start.name}.isdisjoint(attention)


def test_attention_lists_furthest_behind_first(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    slightly = create_project(manager, name="Slightly behind", target_value=100)
    badly = create_project(manager, name="Badly behind", target_value=100)
    log(client, manager, slightly, 35, "2026-06-30")
    log(client, manager, badly, 5, "2026-06-30")

    names = [item["name"] for item in get(client, manager, "attention")]

    assert names == ["Badly behind", "Slightly behind"]


def test_by_type_and_by_state_sums_match_fixture(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove_a = create_project(manager, type=ProjectType.AFFORESTATION, state="Karnataka", unit="trees")
    grove_b = create_project(manager, type=ProjectType.AFFORESTATION, state="Tamil Nadu", unit="Trees")
    solar = create_project(manager, type=ProjectType.SOLAR, state="Karnataka", unit="kW", target_value=50)
    log(client, manager, grove_a, 600, "2026-06-01")  # 60%
    log(client, manager, grove_b, 200, "2026-06-01")  # 20%
    log(client, manager, solar, 40, "2026-06-01")  # 80%

    by_type = {row["type"]: row for row in get(client, manager, "by-type")}
    by_state = {row["state"]: row for row in get(client, manager, "by-state")}

    assert by_type["afforestation"]["project_count"] == 2
    assert by_type["afforestation"]["average_completion_percent"] == 40.0
    assert by_type["solar"]["average_completion_percent"] == 80.0
    assert sum(row["project_count"] for row in by_type.values()) == 3
    assert by_state["Karnataka"] == {
        "state": "Karnataka",
        "project_count": 2,
        "average_completion_percent": 70.0,
        "trees_planted": 600,
    }
    assert by_state["Tamil Nadu"]["trees_planted"] == 200
    assert (
        sum(row["trees_planted"] for row in by_state.values())
        == get(client, manager, "summary")["trees_planted"]
    )
    assert [row["type"] for row in get(client, manager, "by-type")] == [
        "afforestation",
        "solar",
    ]  # largest first


# ---------- the completion rule ----------


def test_completion_averages_capped_percentages_across_units(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove = create_project(manager, target_value=1000, unit="trees")
    solar = create_project(manager, type=ProjectType.SOLAR, target_value=50, unit="kW")
    log(client, manager, grove, 850, "2026-06-01")  # 85%
    log(client, manager, solar, 60, "2026-06-01")  # 120%, counts as 100%

    summary = get(client, manager, "summary")

    # Not (850 + 60) / (1000 + 50): trees and kW cannot be added together.
    assert summary["average_completion_percent"] == 92.5
    assert summary["exceeded_target_count"] == 1
    assert summary["trees_planted"] == 850


def test_cancelled_and_not_started_projects_are_left_out_of_completion(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    counted = create_project(manager, name="Counted", target_value=100)
    create_project(manager, name="Cancelled", status=ProjectStatus.CANCELLED)
    create_project(manager, name="Starts later", status=ProjectStatus.PLANNED, start_date=date(2026, 9, 1))
    log(client, manager, counted, 60, "2026-06-01")

    summary = get(client, manager, "summary")

    assert summary["average_completion_percent"] == 60.0
    assert summary["completion_project_count"] == 1
    assert summary["total_projects"] == 3  # still counted as projects
    assert summary["active_projects"] == 1


def test_tree_unit_is_matched_case_insensitively(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    lower = create_project(manager, unit="trees")
    upper = create_project(manager, unit="Trees")
    other = create_project(manager, unit="saplings")
    log(client, manager, lower, 100, "2026-06-01")
    log(client, manager, upper, 50, "2026-06-01")
    log(client, manager, other, 999, "2026-06-01")

    assert get(client, manager, "summary")["trees_planted"] == 150


# ---------- trend ----------


def test_trend_has_twelve_months_ending_this_month(client: TestClient, manager: User) -> None:
    months = [point["month"] for point in get(client, manager, "trend")]

    assert months[0] == "2025-08"
    assert months[-1] == "2026-07"
    assert len(months) == 12


def test_trend_carries_totals_forward_and_matches_summary(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove = create_project(manager, target_value=1000, start_date=date(2026, 3, 1))
    log(client, manager, grove, 600, "2026-04-15")
    log(client, manager, grove, 850, "2026-06-20")

    trend = {point["month"]: point["average_completion_percent"] for point in get(client, manager, "trend")}

    assert trend["2026-02"] is None  # not started yet
    assert trend["2026-03"] == 0.0  # started, nothing logged
    assert trend["2026-04"] == 60.0
    assert trend["2026-05"] == 60.0  # no update in May: carried forward
    assert trend["2026-06"] == 85.0
    assert trend["2026-07"] == get(client, manager, "summary")["average_completion_percent"]


def test_trend_excludes_cancelled_projects(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    kept = create_project(manager, target_value=100)
    dropped = create_project(manager, target_value=100)
    log(client, manager, kept, 50, "2026-06-01")
    log(client, manager, dropped, 10, "2026-06-01")
    client.patch(f"/api/projects/{dropped.id}", json={"status": "cancelled"}, headers=auth_headers(manager))

    assert get(client, manager, "trend")[-1]["average_completion_percent"] == 50.0


# ---------- filter, consistency, access ----------


def test_type_filter_applies_to_every_endpoint(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove = create_project(manager, type=ProjectType.AFFORESTATION, state="Karnataka", target_value=100)
    solar = create_project(manager, type=ProjectType.SOLAR, state="Goa", target_value=100, unit="kW")
    log(client, manager, grove, 10, "2026-06-30")  # behind
    log(client, manager, solar, 90, "2026-06-30")

    query = "?type=solar"
    assert get(client, manager, "summary", query)["total_projects"] == 1
    assert get(client, manager, "summary", query)["average_completion_percent"] == 90.0
    assert [row["type"] for row in get(client, manager, "by-type", query)] == ["solar"]
    assert [row["state"] for row in get(client, manager, "by-state", query)] == ["Goa"]
    assert get(client, manager, "trend", query)[-1]["average_completion_percent"] == 90.0
    assert get(client, manager, "attention", query) == []
    assert [item["id"] for item in get(client, manager, "attention", "?type=afforestation")] == [grove.id]


def test_dashboard_agrees_with_project_list(
    client: TestClient, manager: User, create_project: CreateProject
) -> None:
    grove = create_project(manager, target_value=1000, unit="trees")
    log(client, manager, grove, 600, "2026-05-01")
    log(client, manager, grove, 850, "2026-06-01")

    listed = client.get("/api/projects", headers=auth_headers(manager)).json()

    assert (
        sum(p["current_value"] for p in listed if p["unit"].lower() == "trees")
        == get(client, manager, "summary")["trees_planted"]
    )


def test_co2_estimate_uses_configured_factor(
    client: TestClient, manager: User, create_project: CreateProject, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dashboard_service.get_settings(), "co2_kg_per_tree_per_year", 25.0)
    grove = create_project(manager, target_value=1000, unit="trees")
    log(client, manager, grove, 400, "2026-06-01")

    summary = get(client, manager, "summary")

    assert summary["estimated_co2_tonnes_per_year"] == 10.0
    assert summary["co2_kg_per_tree_per_year"] == 25.0


@pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
def test_dashboard_requires_login(client: TestClient, endpoint: str) -> None:
    assert client.get(f"/api/dashboard/{endpoint}").status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
def test_viewer_can_read_every_endpoint(client: TestClient, create_user: CreateUser, endpoint: str) -> None:
    get(client, create_user(role=UserRole.VIEWER), endpoint)


@pytest.mark.parametrize(("query", "bad_field"), [("?type=forest", "type"), ("?colour=green", "colour")])
def test_invalid_dashboard_parameters_return_422(
    client: TestClient, manager: User, query: str, bad_field: str
) -> None:
    response = client.get(f"/api/dashboard/summary{query}", headers=auth_headers(manager))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_field in response.json()["fields"]
