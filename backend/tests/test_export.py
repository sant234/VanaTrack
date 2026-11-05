"""Tests for GET /api/export/projects.csv: access, content, filters, and CSV-injection protection."""

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.progress_update import ProgressUpdate
from app.models.project import ProjectStatus, ProjectType
from app.models.user import User, UserRole
from app.services.export_service import COLUMNS, UTF8_BOM, neutralize_formula
from app.services.progress_service import today_in_app_timezone
from tests.conftest import CreateProject, CreateUser, auth_headers

EXPORT_URL = "/api/export/projects.csv"
HEADERS = [header for header, _read in COLUMNS]


@pytest.fixture
def manager(create_user: CreateUser) -> User:
    return create_user(role=UserRole.MANAGER, name="Ravi Kumar")


@pytest.fixture
def viewer(create_user: CreateUser) -> User:
    return create_user(role=UserRole.VIEWER)


def export(client: TestClient, user: User, query: str = ""):
    return client.get(f"{EXPORT_URL}{query}", headers=auth_headers(user))


def parse(response) -> list[dict[str, str]]:
    """The CSV body as a list of {header: cell} rows (the BOM is checked separately)."""
    return list(csv.DictReader(io.StringIO(response.text.removeprefix(UTF8_BOM))))


def add_progress(db: Session, project_id: int, author: User, value: int, previous: int = 0) -> None:
    db.add(
        ProgressUpdate(
            project_id=project_id,
            value=value,
            previous_value=previous,
            recorded_at=datetime(2026, 3, 1, 4, 30, tzinfo=UTC),
            created_by=author.id,
        )
    )
    db.commit()


# ---------- access and file headers ----------


def test_export_requires_login(client: TestClient) -> None:
    response = client.get(EXPORT_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_viewer_downloads_a_csv_file(client: TestClient, viewer: User) -> None:
    response = export(client, viewer)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    filename = f"vanatrack-projects-{today_in_app_timezone().isoformat()}.csv"
    assert response.headers["content-disposition"] == f'attachment; filename="{filename}"'
    assert response.text.startswith(UTF8_BOM)


def test_empty_export_has_only_the_header_row(client: TestClient, viewer: User) -> None:
    response = export(client, viewer)

    lines = response.text.removeprefix(UTF8_BOM).split("\r\n")
    assert lines == [",".join(HEADERS), ""]


# ---------- content ----------


def test_rows_match_the_project_list(
    client: TestClient, db_session: Session, create_project: CreateProject, manager: User, viewer: User
) -> None:
    grove = create_project(
        manager, name="Brief Grove", district="Shivamogga", budget_inr=Decimal("250000.50"), target_value=1000
    )
    add_progress(db_session, grove.id, manager, 600)

    [row] = parse(export(client, viewer))
    [listed] = client.get("/api/projects", headers=auth_headers(viewer)).json()

    assert row == {
        "ID": str(grove.id),
        "Name": "Brief Grove",
        "Type": "afforestation",
        "Status": "active",
        "State": "Karnataka",
        "District": "Shivamogga",
        "Owner": "Ravi Kumar",
        "Unit": "trees",
        "Target": "1000",
        "Current": "600",
        "Progress %": str(listed["progress_percent"]),
        "Expected %": str(listed["expected_percent"]),
        "Behind schedule": "yes" if listed["is_behind_schedule"] else "no",
        "Exceeded target": "no",
        "Start date": "2026-01-01",
        "End date": "2026-12-31",
        "Budget (INR)": "250000.50",
        "Last update": "2026-03-01 10:00",  # 04:30 UTC shown in Asia/Kolkata
    }
    assert listed["current_value"] == 600


def test_blank_optional_fields_are_empty_cells(
    client: TestClient, create_project: CreateProject, manager: User, viewer: User
) -> None:
    create_project(manager, district=None, budget_inr=None)

    [row] = parse(export(client, viewer))

    assert (row["District"], row["Budget (INR)"], row["Last update"], row["Current"]) == ("", "", "", "0")


def test_filters_and_sort_are_the_same_as_the_list(
    client: TestClient, create_project: CreateProject, manager: User, viewer: User
) -> None:
    create_project(manager, name="Bravo Solar", type=ProjectType.SOLAR, unit="kW")
    create_project(manager, name="Alpha Solar", type=ProjectType.SOLAR, unit="kW")
    create_project(manager, name="Grove", type=ProjectType.AFFORESTATION)
    create_project(manager, name="Paused Solar", type=ProjectType.SOLAR, status=ProjectStatus.ON_HOLD)
    query = "?type=solar&status=active&sort=name&order=asc"

    exported = [row["Name"] for row in parse(export(client, viewer, query))]
    listed = [p["name"] for p in client.get(f"/api/projects{query}", headers=auth_headers(viewer)).json()]

    assert exported == ["Alpha Solar", "Bravo Solar"]
    assert exported == listed


def test_search_and_mine_filters_apply(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, manager: User
) -> None:
    other = create_user(role=UserRole.MANAGER)
    create_project(manager, name="Mine Grove")
    create_project(other, name="Their Grove")

    mine = [row["Name"] for row in parse(export(client, manager, "?mine=true"))]
    searched = [row["Name"] for row in parse(export(client, manager, "?search=their"))]

    assert mine == ["Mine Grove"]
    assert searched == ["Their Grove"]


@pytest.mark.parametrize("query", ["?type=rocket", "?status=done", "?state=Atlantis", "?sort=colour"])
def test_invalid_filters_are_422(client: TestClient, viewer: User, query: str) -> None:
    response = export(client, viewer, query)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "VALIDATION_ERROR"


# ---------- CSV injection and escaping ----------


@pytest.mark.parametrize(
    "dangerous_name",
    ['=HYPERLINK("http://evil.example","Click")', "+1+2", "-2+3", "@SUM(A1:A2)", "\tTabbed", "\rReturn"],
)
def test_formula_like_text_is_neutralized(
    client: TestClient, create_project: CreateProject, manager: User, viewer: User, dangerous_name: str
) -> None:
    create_project(manager, name=dangerous_name)

    [row] = parse(export(client, viewer))

    assert row["Name"] == "'" + dangerous_name


def test_formula_check_covers_district_and_owner(
    client: TestClient, create_user: CreateUser, create_project: CreateProject, viewer: User
) -> None:
    sneaky_owner = create_user(role=UserRole.MANAGER, name="=cmd|'/C calc'!A0")
    create_project(sneaky_owner, district="@risky")

    [row] = parse(export(client, viewer))

    assert row["Owner"] == "'=cmd|'/C calc'!A0"
    assert row["District"] == "'@risky"


def test_commas_quotes_and_newlines_stay_in_one_cell(
    client: TestClient, create_project: CreateProject, manager: User, viewer: User
) -> None:
    create_project(manager, name='Lake "Bellandur", phase 2')

    response = export(client, viewer)
    [row] = parse(response)

    assert row["Name"] == 'Lake "Bellandur", phase 2'
    assert '"Lake ""Bellandur"", phase 2"' in response.text


def test_neutralize_formula_leaves_safe_values_alone() -> None:
    assert neutralize_formula("Western Ghats") == "Western Ghats"
    assert neutralize_formula("2026-01-01") == "2026-01-01"
    assert neutralize_formula(-5) == -5  # numbers are not text a spreadsheet would run
    assert neutralize_formula("") == ""
