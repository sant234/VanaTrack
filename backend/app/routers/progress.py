"""Progress endpoints for one project: read the history, log a new total, undo the latest entry.

There is deliberately no PUT/PATCH: the log is append-only. Mistakes are fixed with a correction entry.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_project_owner_or_admin, require_roles
from app.models.progress_update import ProgressUpdate
from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.progress import AuthorOut, ProgressCreate, ProgressUpdateOut
from app.services import progress_service
from app.services.project_service import get_project_or_404

router = APIRouter(prefix="/projects/{project_id}/progress", tags=["progress"])


def _to_out(update: ProgressUpdate, can_delete: bool) -> ProgressUpdateOut:
    return ProgressUpdateOut(
        id=update.id,
        value=update.value,
        previous_value=update.previous_value,
        change=update.value - update.previous_value,
        is_correction=update.is_correction,
        note=update.note,
        recorded_at=update.recorded_at,
        created_at=update.created_at,
        author=AuthorOut.model_validate(update.author),
        can_delete=can_delete,
    )


@router.get("", response_model=list[ProgressUpdateOut])
def list_progress(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProgressUpdateOut]:
    """The full history, newest first. Everyone logged in may read it."""
    get_project_or_404(db, project_id)
    updates = progress_service.list_updates(db, project_id)
    is_admin = current_user.role == UserRole.ADMIN
    # Only the newest entry (first in the list) can be undone, and only by an admin.
    return [_to_out(update, can_delete=is_admin and index == 0) for index, update in enumerate(updates)]


@router.post("", response_model=ProgressUpdateOut, status_code=status.HTTP_201_CREATED)
def log_progress(
    data: ProgressCreate,
    project: Project = Depends(require_project_owner_or_admin),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressUpdateOut:
    """Record a new running total. Only the project's owning manager or an admin."""
    update = progress_service.log_progress(db, project, data, author=current_user)
    return _to_out(update, can_delete=current_user.role == UserRole.ADMIN)


@router.delete("/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_latest_progress(
    project_id: int,
    update_id: int,
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    """Admins only, and only the newest entry (an "undo" for an obvious mistake)."""
    project = get_project_or_404(db, project_id)
    progress_service.delete_latest_update(db, project, update_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
