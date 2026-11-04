"""Health check: lets us (and the hosting platform) confirm the API and database are up."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Return 200 when the database answers, or 503 when it can't be reached."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # 503 (not 200) so monitoring tools know the service is not fully working.
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unreachable"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "database": "ok"})
