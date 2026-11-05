"""Business rules for projects: listing with filters, create, update, delete."""

from datetime import date

from fastapi import status
from sqlalchemy import ColumnElement, Row
from sqlalchemy.orm import Session

from app.errors import AppError, field_validation_error
from app.models.activity_log import ActivityAction, ActivityEntityType
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
from app.services.activity_service import record_activity, to_json_value
from app.services.progress_service import (
    ProgressColumns,
    build_progress,
    select_projects_with_progress,
    today_in_app_timezone,
)

LIKE_ESCAPE_CHAR = "\\"


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
        is_target_exceeded=progress.is_target_exceeded,
        last_updated_at=progress.last_updated_at,
        can_edit=can_edit_project(viewer, project),
    )


def _escape_like(text: str) -> str:
    """Make % and _ in a search box match literally instead of acting as SQL wildcards."""
    for special in (LIKE_ESCAPE_CHAR, "%", "_"):
        text = text.replace(special, LIKE_ESCAPE_CHAR + special)
    return text


def _sort_column(sort: ProjectSort, progress: ProgressColumns) -> ColumnElement:
    columns = {
        ProjectSort.NAME: Project.name,
        ProjectSort.CREATED_AT: Project.created_at,
        ProjectSort.END_DATE: Project.end_date,
        ProjectSort.PROGRESS: progress.progress_percent,
    }
    return columns[sort]


def list_projects(db: Session, params: ProjectListParams, viewer: User) -> list[ProjectOut]:
    # The same query (and so the same numbers) as the detail page: see progress_service.
    query, progress = select_projects_with_progress()
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

    sort_column = _sort_column(params.sort, progress)
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
    query, _progress = select_projects_with_progress()
    row = db.execute(query.where(Project.id == project_id)).first()
    if row is None:
        raise project_not_found_error()
    return _to_project_out(row, viewer, today_in_app_timezone())


def create_project(db: Session, data: ProjectCreate, owner: User) -> Project:
    """The person who creates a project becomes its owner. The project and its log entry share one commit."""
    project = Project(**data.model_dump(), owner_id=owner.id)
    db.add(project)
    db.flush()  # assigns project.id, which the activity entry needs
    record_activity(
        db,
        owner,
        ActivityAction.CREATED,
        ActivityEntityType.PROJECT,
        project.id,
        project.id,
        {"name": project.name},
    )
    db.commit()
    return project


def _changed_fields(project: Project, sent: dict[str, object]) -> dict[str, dict[str, object]]:
    """Of the fields sent, only those whose value really differs, as {"field": {"from": .., "to": ..}}."""
    return {
        field_name: {"from": to_json_value(getattr(project, field_name)), "to": to_json_value(new_value)}
        for field_name, new_value in sent.items()
        if getattr(project, field_name) != new_value
    }


def update_project(db: Session, project: Project, data: ProjectUpdate, editor: User) -> Project:
    """Change only the fields that were sent. Dates are checked against the saved values too.

    Sending a value equal to the saved one is not a change: if nothing differs, nothing is written,
    and no activity entry is recorded.
    """
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

    changed = _changed_fields(project, changes)
    if not changed:
        return project

    for field_name in changed:
        setattr(project, field_name, changes[field_name])
    record_activity(
        db,
        editor,
        ActivityAction.UPDATED,
        ActivityEntityType.PROJECT,
        project.id,
        project.id,
        {"name": project.name, "changes": changed},
    )
    db.commit()
    return project


def delete_project(db: Session, project: Project, deleted_by: User) -> None:
    """Delete the project in one transaction.

    Related rows are handled by the database's ON DELETE rules (see DATABASE.md, "Deletion policy"):
    progress updates are deleted with the project; activity entries stay, with project_id set to NULL.
    The "deleted" entry is written first, linked to the project, so the same SET NULL rule unlinks it;
    the name in details keeps it readable afterwards.
    """
    record_activity(
        db,
        deleted_by,
        ActivityAction.DELETED,
        ActivityEntityType.PROJECT,
        project.id,
        project.id,
        {"name": project.name},
    )
    db.flush()  # insert the entry before the DELETE, so the database's SET NULL applies to it too
    db.delete(project)
    db.commit()
