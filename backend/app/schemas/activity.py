"""Shapes of activity-log data going in and out of the API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.activity_log import ActivityAction

ACTIVITY_DEFAULT_LIMIT = 50
ACTIVITY_MAX_LIMIT = 100


class ActivityListParams(BaseModel):
    """Query string of GET /activity. A limit above the maximum is a 422, not silently capped."""

    limit: int = Field(default=ACTIVITY_DEFAULT_LIMIT, ge=1, le=ACTIVITY_MAX_LIMIT)
    project_id: int | None = None


class ActivityOut(BaseModel):
    id: int
    action: ActivityAction
    entity_type: str
    entity_id: int
    # NULL once the project is deleted; project_name then comes from the name saved in details.
    project_id: int | None
    project_name: str | None
    user_id: int
    user_name: str
    created_at: datetime
    details: dict[str, Any]
    # Written by the server, so every client shows the same sentence.
    summary: str
