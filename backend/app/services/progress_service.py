"""The single source of truth for project progress and schedule figures.

Nothing here is stored in the database. Every value is recalculated on each request,
so the project list, project detail, dashboard and CSV export can never disagree.

Prompt 2: there are no progress updates yet, so every project's current value is 0.
Prompt 3 replaces current_value_column() and last_updated_column() with "the latest progress update".
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, DateTime, Integer, Numeric, cast, func, literal, null

from app.config import get_settings
from app.models.project import Project, ProjectStatus

PERCENT = 100
PERCENT_DECIMALS = 1
# A project counts as "behind schedule" when its progress trails the timeline by more than this.
BEHIND_SCHEDULE_TOLERANCE_POINTS = 10


# ---------- SQL pieces (used inside queries, so the list can be sorted by progress) ----------


def current_value_column() -> ColumnElement[int]:
    """The project's current achieved value. Placeholder until Prompt 3 adds progress updates."""
    return literal(0, type_=Integer)


def last_updated_column() -> ColumnElement[datetime]:
    """When progress was last logged. Placeholder until Prompt 3."""
    return cast(null(), DateTime(timezone=True))


def progress_percent_column() -> ColumnElement[float]:
    """current / target x 100, rounded to one decimal place (target is always > 0)."""
    ratio = cast(current_value_column(), Numeric) * PERCENT / Project.target_value
    return func.round(ratio, PERCENT_DECIMALS)


# ---------- Plain Python rules (small, pure functions that are easy to test) ----------


def today_in_app_timezone() -> date:
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


def expected_percent(start_date: date, end_date: date, today: date) -> float:
    """How much of the project's timeline has passed, from 0 to 100."""
    if today <= start_date:
        return 0.0
    if today >= end_date:
        return float(PERCENT)
    elapsed_days = (today - start_date).days
    total_days = (end_date - start_date).days
    return round(elapsed_days * PERCENT / total_days, PERCENT_DECIMALS)


def is_behind_schedule(status: ProjectStatus, progress: float, expected: float) -> bool:
    """Only active projects can be behind; planned, paused or finished ones are not judged."""
    return status == ProjectStatus.ACTIVE and progress < expected - BEHIND_SCHEDULE_TOLERANCE_POINTS


@dataclass(frozen=True)
class ProjectProgress:
    current_value: int
    progress_percent: float
    expected_percent: float
    is_behind_schedule: bool
    last_updated_at: datetime | None


def build_progress(
    project: Project,
    current_value: int,
    progress_percent: float,
    last_updated_at: datetime | None,
    today: date,
) -> ProjectProgress:
    expected = expected_percent(project.start_date, project.end_date, today)
    progress = float(progress_percent)
    return ProjectProgress(
        current_value=current_value,
        progress_percent=progress,
        expected_percent=expected,
        is_behind_schedule=is_behind_schedule(project.status, progress, expected),
        last_updated_at=last_updated_at,
    )
