"""Project endpoints: list, options, create, read, update, delete."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.constants import INDIAN_STATES_AND_UNION_TERRITORIES
from app.database import get_db
from app.deps import get_current_user, require_project_owner_or_admin, require_roles
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User, UserRole
from app.schemas.project import (
    OptionOut,
    ProjectCreate,
    ProjectListParams,
    ProjectOptions,
    ProjectOut,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _label(value: str) -> str:
    """Turn an enum value into a readable label, e.g. water_conservation -> Water conservation."""
    return value.replace("_", " ").capitalize()


@router.get("", response_model=list[ProjectOut])
def list_projects(
    params: Annotated[ProjectListParams, Query()],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    return project_service.list_projects(db, params, current_user)


# Declared before "/{project_id}" so "options" is not mistaken for a project id.
@router.get("/options", response_model=ProjectOptions)
def project_options(_current_user: User = Depends(get_current_user)) -> ProjectOptions:
    """Allowed values for the form and filter dropdowns, so the frontend never keeps its own copy."""
    return ProjectOptions(
        types=[OptionOut(value=item.value, label=_label(item.value)) for item in ProjectType],
        statuses=[OptionOut(value=item.value, label=_label(item.value)) for item in ProjectStatus],
        states=list(INDIAN_STATES_AND_UNION_TERRITORIES),
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = project_service.create_project(db, data, owner=current_user)
    return project_service.get_project_out(db, project.id, current_user)


@router.get("/{project_id}", response_model=ProjectOut)
def read_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    return project_service.get_project_out(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    data: ProjectUpdate,
    project: Project = Depends(require_project_owner_or_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project_service.update_project(db, project, data, editor=current_user)
    return project_service.get_project_out(db, project.id, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project: Project = Depends(require_project_owner_or_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    project_service.delete_project(db, project, deleted_by=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
