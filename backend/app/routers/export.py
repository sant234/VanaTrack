"""CSV export. Any logged-in user may download; it takes the same filters and sort as GET /projects."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.project import ProjectListParams
from app.services import export_service, project_service
from app.services.progress_service import today_in_app_timezone

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/projects.csv", response_class=Response)
def export_projects_csv(
    params: Annotated[ProjectListParams, Query()],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """The project list as a CSV file, exactly as the list shows it for the same filters."""
    projects = project_service.list_projects(db, params, current_user)
    filename = export_service.export_filename(today_in_app_timezone())
    return Response(
        content=export_service.build_projects_csv(projects),
        media_type=CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
