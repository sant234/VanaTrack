"""Activity endpoint: the organisation-wide log, or one project's part of it. Read-only."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas.activity import ActivityListParams, ActivityOut
from app.services import activity_service
from app.services.project_service import get_project_or_404

# Every logged-in user may read the log, whatever their role.
router = APIRouter(prefix="/activity", tags=["activity"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ActivityOut])
def list_activity(
    params: Annotated[ActivityListParams, Query()],
    db: Session = Depends(get_db),
) -> list[ActivityOut]:
    """Newest first. With ?project_id=, only that project's entries (404 if it does not exist)."""
    if params.project_id is not None:
        get_project_or_404(db, params.project_id)
    return activity_service.list_activity(db, params.limit, params.project_id)
