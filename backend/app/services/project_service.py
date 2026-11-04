"""Business rules for projects: listing with filters, create, update, delete."""

from datetime import date

from fastapi import status
from sqlalchemy import ColumnElement, Row, Select, select
from sqlalchemy.orm import Session, joinedload

from app.errors import AppError, field_validation_error
from app.models.project import Project
from app.models.user import User
from app.permissions import can_edit_project
from app.schemas.project import (
    OwnerOut,
    ProjectCreate,
    ProjectListParams,
    ProjectOut,
    ProjectSort,
    ProjectUpdate,
    SortOrder,
)
from app.services.progress_service import (
    build_progress,
    current_value_column,
    last_updated_column,
    progress_percent_column,
    today_in_app_timezone,
)

LIKE_ESCAPE_CHAR = "\\"


def _projects_with_progress() -> Select:
    """One query shape for both list and detail, so both always show the same progress numbers."""
    return select(
        Project,
        current_value_column().label("current_value"),
        progress_percent_column().label("progress_percent"),
        last_updated_column().label("last_updated_at"),
    ).options(joinedload(Project.owner))


def _to_project_out(row: Row, viewer: User, today: date) -> ProjectOut:
    project: Project = row.Project
    progress = build_progress(project, row.current_value, row.progress_percent, row.last_updated_at, today)
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        type=project.type,
        status=project.status,
        target_value=project.target_value,
        unit=project.unit,
        state=project.state,
        district=project.district,
        start_date=project.start_date,
        end_date=project.end_date,
        budget_inr=project.budget_inr,
        owner=OwnerOut.model_validate(project.owner),
        created_at=project.created_at,
        updated_at=project.updated_at,
        current_value=progress.current_value,
        progress_percent=progress.progress_percent,
        expected_percent=progress.expected_percent,
        is_behind_schedule=progress.is_behind_schedule,
        last_updated_at=progress.last_updated_at,
        can_edit=can_edit_project(viewer, project),
    )


def _escape_like(text: str) -> str:
    """Make % and _ in a search box match literally instead of acting as SQL wildcards."""
    for special in (LIKE_ESCAPE_CHAR, "%", "_"):
        text = text.replace(special, LIKE_ESCAPE_CHAR + special)
    return text


def _sort_column(sort: ProjectSort) -> ColumnElement:
    columns = {
        ProjectSort.NAME: Project.name,
        ProjectSort.CREATED_AT: Project.created_at,
        ProjectSort.END_DATE: Project.end_date,
        ProjectSort.PROGRESS: progress_percent_column(),
    }
    return columns[sort]


def list_projects(db: Session, params: ProjectListParams, viewer: User) -> list[ProjectOut]:
    query = _projects_with_progress()
    if params.search:
        query = query.where(Project.name.ilike(f"%{_escape_like(params.search)}%", escape=LIKE_ESCAPE_CHAR))
    if params.type:
        query = query.where(Project.type == params.type)
    if params.status:
        query = query.where(Project.status == params.status)
    if params.state:
        query = query.where(Project.state == params.state)
    if params.mine:
        query = query.where(Project.owner_id == viewer.id)

    sort_column = _sort_column(params.sort)
    if params.order == SortOrder.DESC:
        # Project id breaks ties, so the order is stable when two projects share a value.
        query = query.order_by(sort_column.desc(), Project.id.desc())
    else:
        query = query.order_by(sort_column.asc(), Project.id.asc())

    today = today_in_app_timezone()
    return [_to_project_out(row, viewer, today) for row in db.execute(query)]


def project_not_found_error() -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "PROJECT_NOT_FOUND", "Project not found.")


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise project_not_found_error()
    return project


def get_project_out(db: Session, project_id: int, viewer: User) -> ProjectOut:
    row = db.execute(_projects_with_progress().where(Project.id == project_id)).first()
    if row is None:
        raise project_not_found_error()
    return _to_project_out(row, viewer, today_in_app_timezone())


def create_project(db: Session, data: ProjectCreate, owner: User) -> Project:
    """The person who creates a project becomes its owner."""
    project = Project(**data.model_dump(), owner_id=owner.id)
    db.add(project)
    db.commit()
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate) -> Project:
    """Change only the fields that were sent. Dates are checked against the saved values too."""
    changes = data.model_dump(exclude_unset=True)
    start_date = changes.get("start_date", project.start_date)
    end_date = changes.get("end_date", project.end_date)
    if end_date < start_date:
        field = "end_date" if "end_date" in changes else "start_date"
        message = (
            "End date cannot be before the start date."
            if field == "end_date"
            else "Start date cannot be after the end date."
        )
        raise field_validation_error({field: message})

    for field_name, value in changes.items():
        setattr(project, field_name, value)
    db.commit()
    return project


def delete_project(db: Session, project: Project) -> None:
    """Delete the project in one transaction.

    Related rows are handled by the database's ON DELETE rules (see DATABASE.md, "Deletion policy"):
    child records are deleted with the project, history keeps its entry with the link cleared.
    """
    db.delete(project)
    db.commit()
