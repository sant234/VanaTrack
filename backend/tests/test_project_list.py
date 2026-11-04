"""Tests for GET /api/projects: search, filters, "mine", and sorting."""

from datetime import date

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.project import ProjectStatus, ProjectType
from app.models.user import User, UserRole
from tests.conftest import CreateProject, CreateUser, auth_headers

PROJECTS_URL = "/api/projects"


@pytest.fixture
def owners(create_user: CreateUser) -> tuple[User, User]:
    return create_user(role=UserRole.MANAGER, name="Ravi"), create_user(role=UserRole.MANAGER, name="Meera")


@pytest.fixture
def sample_projects(create_project: CreateProject, owners: tuple[User, User]) -> None:
    ravi, meera = owners
    create_project(
        ravi,
        name="Mangrove Belt",
        type=ProjectType.AFFORESTATION,
        state="Tamil Nadu",
        end_date=date(2026, 6, 30),
    )
    create_project(
        ravi,
        name="Rooftop Solar 50kW",
        type=ProjectType.SOLAR,
        status=ProjectStatus.PLANNED,
        state="Karnataka",
        unit="kw",
        end_date=date(2026, 9, 30),
    )
    create_project(
        meera,
        name="Lake Revival",
        type=ProjectType.WATER_CONSERVATION,
        state="Karnataka",
        unit="kl water",
        end_date=date(2026, 3, 31),
    )
    create_project(meera, name="100%_Recycled Drive", type=ProjectType.WASTE_MANAGEMENT, state="Maharashtra")


def names(client: TestClient, user: User, query: str = "") -> list[str]:
    response = client.get(f"{PROJECTS_URL}{query}", headers=auth_headers(user))
    assert response.status_code == status.HTTP_200_OK, response.text
    return [project["name"] for project in response.json()]


@pytest.mark.usefixtures("sample_projects")
def test_list_returns_all_projects_to_any_logged_in_user(client: TestClient, create_user: CreateUser) -> None:
    viewer = create_user(role=UserRole.VIEWER)
    assert len(names(client, viewer)) == 4


def test_list_requires_login(client: TestClient) -> None:
    assert client.get(PROJECTS_URL).status_code == status.HTTP_401_UNAUTHORIZED


def test_list_is_empty_when_there_are_no_projects(client: TestClient, create_user: CreateUser) -> None:
    assert names(client, create_user()) == []


@pytest.mark.usefixtures("sample_projects")
def test_search_matches_part_of_name_ignoring_case(client: TestClient, owners: tuple[User, User]) -> None:
    assert names(client, owners[0], "?search=SOLAR") == ["Rooftop Solar 50kW"]


@pytest.mark.usefixtures("sample_projects")
def test_search_treats_percent_and_underscore_literally(
    client: TestClient, owners: tuple[User, User]
) -> None:
    assert names(client, owners[0], "?search=100%25_") == ["100%_Recycled Drive"]
    assert names(client, owners[0], "?search=%25") == ["100%_Recycled Drive"]


@pytest.mark.usefixtures("sample_projects")
def test_blank_search_is_ignored(client: TestClient, owners: tuple[User, User]) -> None:
    assert len(names(client, owners[0], "?search=%20%20")) == 4


@pytest.mark.usefixtures("sample_projects")
@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?type=solar", ["Rooftop Solar 50kW"]),
        ("?status=planned", ["Rooftop Solar 50kW"]),
        ("?state=karnataka&sort=name&order=asc", ["Lake Revival", "Rooftop Solar 50kW"]),
        ("?state=Karnataka&type=water_conservation", ["Lake Revival"]),
        ("?type=solar&status=active", []),
    ],
)
def test_filters_narrow_the_list(
    client: TestClient, owners: tuple[User, User], query: str, expected: list[str]
) -> None:
    assert names(client, owners[0], query) == expected


@pytest.mark.usefixtures("sample_projects")
def test_mine_shows_only_my_projects(client: TestClient, owners: tuple[User, User]) -> None:
    ravi, _meera = owners
    assert sorted(names(client, ravi, "?mine=true")) == ["Mangrove Belt", "Rooftop Solar 50kW"]


@pytest.mark.usefixtures("sample_projects")
def test_sort_by_name_both_directions(client: TestClient, owners: tuple[User, User]) -> None:
    ascending = names(client, owners[0], "?sort=name&order=asc")
    assert ascending == sorted(ascending)
    assert names(client, owners[0], "?sort=name&order=desc") == list(reversed(ascending))


@pytest.mark.usefixtures("sample_projects")
def test_sort_by_end_date(client: TestClient, owners: tuple[User, User]) -> None:
    assert names(client, owners[0], "?sort=end_date&order=asc")[:3] == [
        "Lake Revival",
        "Mangrove Belt",
        "Rooftop Solar 50kW",
    ]


@pytest.mark.usefixtures("sample_projects")
def test_default_sort_is_newest_first(client: TestClient, owners: tuple[User, User]) -> None:
    # Same created_at inside one test transaction, so the id tie-breaker decides: last created first.
    assert names(client, owners[0])[0] == "100%_Recycled Drive"


@pytest.mark.usefixtures("sample_projects")
def test_sort_by_progress_is_accepted(client: TestClient, owners: tuple[User, User]) -> None:
    assert len(names(client, owners[0], "?sort=progress&order=desc")) == 4


@pytest.mark.parametrize(
    ("query", "bad_field"),
    [
        ("?sort=popularity", "sort"),
        ("?order=sideways", "order"),
        ("?type=forest", "type"),
        ("?state=Atlantis", "state"),
        ("?mine=perhaps", "mine"),
        ("?unknown=1", "unknown"),
        (f"?search={'x' * 101}", "search"),
    ],
)
def test_invalid_list_parameters_return_422(
    client: TestClient, create_user: CreateUser, query: str, bad_field: str
) -> None:
    response = client.get(f"{PROJECTS_URL}{query}", headers=auth_headers(create_user()))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_field in response.json()["fields"]
