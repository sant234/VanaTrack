"""The activity log: write one entry per change, read the feed, and phrase each entry for people.

record_activity only ADDS the row to the caller's session and never commits. The caller's own commit
saves the change and its log entry together; if the change fails and is rolled back, so is the entry.
That is what keeps the log honest: a rejected request (400/403/422) never leaves an entry behind.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.activity_log import ActivityAction, ActivityEntityType, ActivityLog
from app.models.user import User
from app.schemas.activity import ActivityOut

DELETED_PROJECT_LABEL = "a deleted project"

# Readable names for project fields in "updated" summaries; unknown fields fall back to the raw name.
FIELD_LABELS = {
    "target_value": "target",
    "start_date": "start date",
    "end_date": "end date",
    "budget_inr": "budget",
}


def record_activity(
    db: Session,
    user: User,
    action: ActivityAction,
    entity_type: ActivityEntityType,
    entity_id: int,
    project_id: int | None,
    details: dict[str, Any],
) -> ActivityLog:
    """Add an activity entry to the current transaction. Does NOT commit: the caller's commit saves it."""
    entry = ActivityLog(
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        details=details,
    )
    db.add(entry)
    return entry


def to_json_value(value: object) -> object:
    """Turn a project field value into something JSON can store (dates, money and enums are not)."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        # NUMERIC(14, 2) has at most 14 significant digits, which a float holds exactly enough to show.
        return float(value)
    return value


def list_activity(db: Session, limit: int, project_id: int | None) -> list[ActivityOut]:
    """Newest first. id breaks ties, because rows saved in one transaction share the same created_at."""
    query = (
        select(ActivityLog)
        .options(joinedload(ActivityLog.user), joinedload(ActivityLog.project))
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
    )
    if project_id is not None:
        query = query.where(ActivityLog.project_id == project_id)
    return [_to_activity_out(entry) for entry in db.scalars(query)]


def _project_name(entry: ActivityLog) -> str | None:
    """The live name while the project exists; after deletion, the name copied into details."""
    if entry.project is not None:
        return entry.project.name
    return entry.details.get("name")


def _to_activity_out(entry: ActivityLog) -> ActivityOut:
    project_name = _project_name(entry)
    return ActivityOut(
        id=entry.id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        project_id=entry.project_id,
        project_name=project_name,
        user_id=entry.user_id,
        user_name=entry.user.name,
        created_at=entry.created_at,
        details=entry.details,
        summary=build_summary(entry.action, entry.user.name, project_name, entry.details),
    )


# ---------- human-readable summaries ----------


def _changed_fields(details: dict[str, Any]) -> str:
    fields = details.get("changes", {}).keys()
    return ", ".join(FIELD_LABELS.get(field, field) for field in fields)


def _progress_logged(actor: str, project: str, details: dict[str, Any]) -> str:
    correction = " (correction)" if details.get("is_correction") else ""
    return f"{actor} logged progress on {project}: {details['from']} → {details['to']}{correction}"


SummaryBuilder = Callable[[str, str, dict[str, Any]], str]

SUMMARY_BUILDERS: dict[ActivityAction, SummaryBuilder] = {
    ActivityAction.CREATED: lambda actor, project, _details: f"{actor} created project {project}",
    ActivityAction.UPDATED: lambda actor, project, details: (
        f"{actor} updated {project}: {_changed_fields(details)}"
    ),
    ActivityAction.DELETED: lambda actor, project, _details: f"{actor} deleted project {project}",
    ActivityAction.PROGRESS_LOGGED: _progress_logged,
    ActivityAction.PROGRESS_DELETED: lambda actor, project, details: (
        f"{actor} undid the progress entry {details['from']} → {details['to']} on {project}"
    ),
    ActivityAction.ROLE_CHANGED: lambda actor, _project, details: (
        f"{actor} changed {details['email']}'s role from {details['from']} to {details['to']}"
    ),
    ActivityAction.USER_DEACTIVATED: lambda actor, _project, details: (
        f"{actor} deactivated {details['email']}"
    ),
    ActivityAction.USER_ACTIVATED: lambda actor, _project, details: f"{actor} reactivated {details['email']}",
}


def build_summary(
    action: ActivityAction, actor_name: str, project_name: str | None, details: dict[str, Any]
) -> str:
    """One sentence for the feed, e.g. "Field Manager logged progress on Western Ghats: 600 → 850"."""
    return SUMMARY_BUILDERS[action](actor_name, project_name or DELETED_PROJECT_LABEL, details)
