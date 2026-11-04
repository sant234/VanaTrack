"""Schedule maths, tested with fixed dates so results never depend on when the tests run."""

from datetime import date

import pytest

from app.models.project import ProjectStatus
from app.services.progress_service import expected_percent, is_behind_schedule

START = date(2026, 1, 1)
END = date(2026, 12, 31)  # 364 days later


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2025, 12, 1), 0.0),  # not started yet
        (START, 0.0),  # first day
        (date(2026, 7, 2), 50.0),  # 182 of 364 days
        (END, 100.0),  # last day
        (date(2027, 3, 1), 100.0),  # already over
    ],
)
def test_expected_percent_follows_the_timeline(today: date, expected: float) -> None:
    assert expected_percent(START, END, today) == expected


def test_one_day_project_does_not_divide_by_zero() -> None:
    assert expected_percent(START, START, START) == 0.0
    assert expected_percent(START, START, date(2026, 1, 2)) == 100.0


def test_active_project_more_than_10_points_behind_is_behind_schedule() -> None:
    assert is_behind_schedule(ProjectStatus.ACTIVE, progress=39.0, expected=50.0)


def test_active_project_within_10_points_is_on_track() -> None:
    assert not is_behind_schedule(ProjectStatus.ACTIVE, progress=40.0, expected=50.0)


@pytest.mark.parametrize(
    "status", [ProjectStatus.PLANNED, ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
)
def test_only_active_projects_can_be_behind_schedule(status: ProjectStatus) -> None:
    assert not is_behind_schedule(status, progress=0.0, expected=90.0)
