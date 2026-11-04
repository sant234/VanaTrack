"""The single source of truth for project progress.

Two jobs:
1. READ: work out each project's current value, progress % and schedule figures. Nothing is stored;
   every value comes from the latest progress update, so list, detail, dashboard and export can
   never disagree.
2. WRITE: append a progress update after checking every rule in ARCHITECTURE.md 7.2.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from fastapi import status
from sqlalchemy import ColumnElement, Numeric, Select, cast, func, select, true
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.errors import AppError, field_validation_error
from app.models.progress_update import ProgressUpdate
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.progress import ProgressCreate

PERCENT = 100
PERCENT_DECIMALS = 1
# A project counts as "behind schedule" when its progress trails the timeline by more than this.
BEHIND_SCHEDULE_TOLERANCE_POINTS = 10
# A new total above target x this is almost certainly a typo (e.g. an extra zero).
UNREALISTIC_TARGET_MULTIPLIER = 10
CLOSED_STATUSES = (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)


# ---------- READ: derived values, built once in SQL ----------


@dataclass(frozen=True)
class ProgressColumns:
    """SQL expressions for the derived values, plus the subquery they come from."""

    latest_update: object  # LATERAL subquery: the newest progress update of the current project row
    current_value: ColumnElement[int]
    progress_percent: ColumnElement[float]
    last_updated_at: ColumnElement[datetime]


def progress_columns() -> ProgressColumns:
    """current value = the latest update's value (0 if none); progress % = current / target x 100.

    LATERAL means "for each project row, run this small query": take its newest update.
    The (project_id, recorded_at DESC, id DESC) index makes that a single index lookup.
    """
    latest = (
        select(ProgressUpdate.value, ProgressUpdate.recorded_at)
        .where(ProgressUpdate.project_id == Project.id)
        .order_by(ProgressUpdate.recorded_at.desc(), ProgressUpdate.id.desc())
        .limit(1)
        .lateral("latest_update")
    )
    current_value = func.coalesce(latest.c.value, 0)
    progress_percent = func.round(
        cast(current_value, Numeric) * PERCENT / Project.target_value, PERCENT_DECIMALS
    )
    return ProgressColumns(latest, current_value, progress_percent, latest.c.recorded_at)


def select_projects_with_progress() -> tuple[Select, ProgressColumns]:
    """SELECT every project together with its derived progress columns.

    Callers add their own WHERE / ORDER BY. Returns the columns too, so callers can sort by them.
    """
    columns = progress_columns()
    query = (
        select(
            Project,
            columns.current_value.label("current_value"),
            columns.progress_percent.label("progress_percent"),
            columns.last_updated_at.label("last_updated_at"),
        )
        .outerjoin(columns.latest_update, true())  # outer: projects with no updates still appear (as 0)
        .options(joinedload(Project.owner))
    )
    return query, columns


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
    is_target_exceeded: bool
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
        # Also true when an edit lowers the target below what was already achieved (ARCHITECTURE 7.2).
        is_target_exceeded=current_value > project.target_value,
        last_updated_at=last_updated_at,
    )


# ---------- READ: the history ----------


def get_latest_update(db: Session, project_id: int) -> ProgressUpdate | None:
    return db.scalar(
        select(ProgressUpdate)
        .where(ProgressUpdate.project_id == project_id)
        .order_by(ProgressUpdate.recorded_at.desc(), ProgressUpdate.id.desc())
        .limit(1)
    )


def list_updates(db: Session, project_id: int) -> list[ProgressUpdate]:
    """The full history, newest first, with the author of each entry."""
    return list(
        db.scalars(
            select(ProgressUpdate)
            .where(ProgressUpdate.project_id == project_id)
            .options(joinedload(ProgressUpdate.author))
            .order_by(ProgressUpdate.recorded_at.desc(), ProgressUpdate.id.desc())
        )
    )


# ---------- WRITE: append an update ----------


def _progress_error(code: str, message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, code, message)


def _check_recorded_at(project: Project, latest: ProgressUpdate | None, recorded_at: datetime) -> None:
    """The log must read in time order, so "previous_value" is always the total just before."""
    app_zone = ZoneInfo(get_settings().app_timezone)
    if recorded_at.astimezone(app_zone).date() < project.start_date:
        raise field_validation_error(
            {"recorded_at": f"The date cannot be before the project start date ({project.start_date})."}
        )
    if latest is not None and recorded_at < latest.recorded_at:
        latest_day = latest.recorded_at.astimezone(app_zone).date()
        raise field_validation_error(
            {"recorded_at": f"The date cannot be before the latest update ({latest_day})."}
        )


def _check_new_total(project: Project, current_value: int, data: ProgressCreate) -> None:
    if data.value == current_value:
        raise _progress_error(
            "PROGRESS_NO_CHANGE", f"The new total is the same as the current total ({current_value})."
        )
    if data.value < current_value and not data.is_correction:
        raise _progress_error(
            "PROGRESS_DECREASE_REQUIRES_NOTE",
            f"The total would go down ({current_value} → {data.value}). "
            "Mark this as a correction and explain the reason.",
        )
    if data.value > project.target_value * UNREALISTIC_TARGET_MULTIPLIER:
        raise _progress_error(
            "PROGRESS_UNREALISTIC",
            f"{data.value} is more than {UNREALISTIC_TARGET_MULTIPLIER}× the target "
            f"({project.target_value}). Please check for a typo.",
        )


def log_progress(db: Session, project: Project, data: ProgressCreate, author: User) -> ProgressUpdate:
    """Append a new running total, after checking every rule. One transaction.

    The project row is locked first (SELECT ... FOR UPDATE), so two people saving at the same moment
    are handled one after the other and both cannot record the same "previous_value".
    """
    db.execute(select(Project.id).where(Project.id == project.id).with_for_update())
    db.refresh(project)

    if project.status in CLOSED_STATUSES:
        raise _progress_error(
            "PROJECT_CLOSED", f"Progress cannot be logged on a {project.status.replace('_', ' ')} project."
        )

    latest = get_latest_update(db, project.id)
    current_value = latest.value if latest else 0
    recorded_at = data.recorded_at or datetime.now(UTC)
    _check_recorded_at(project, latest, recorded_at)
    _check_new_total(project, current_value, data)

    update = ProgressUpdate(
        project_id=project.id,
        value=data.value,
        previous_value=current_value,
        is_correction=data.is_correction,
        note=data.note,
        recorded_at=recorded_at,
        created_by=author.id,
    )
    db.add(update)
    db.commit()
    db.refresh(update, attribute_names=["author"])
    return update


# ---------- WRITE: undo the latest update (admin only) ----------


def delete_latest_update(db: Session, project: Project, update_id: int) -> None:
    """Remove an update, but only the newest one.

    Removing an older entry would leave the next entry's previous_value pointing at a total that no
    longer exists in the history. For older mistakes, add a correction instead.
    """
    db.execute(select(Project.id).where(Project.id == project.id).with_for_update())
    update = db.get(ProgressUpdate, update_id)
    if update is None or update.project_id != project.id:
        raise AppError(status.HTTP_404_NOT_FOUND, "PROGRESS_UPDATE_NOT_FOUND", "Progress update not found.")

    latest = get_latest_update(db, project.id)
    if latest is None or latest.id != update.id:
        raise _progress_error(
            "PROGRESS_NOT_LATEST",
            "Only the most recent update can be deleted. To fix an older entry, add a correction.",
        )
    db.delete(update)
    db.commit()
