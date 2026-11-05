"""The activity_logs table: an append-only record of who changed what, and when.

One row is written in the same transaction as the change it describes (ARCHITECTURE.md 7.5), so a
change and its log entry are saved together or not at all. No endpoint edits or deletes these rows.

Deletion policy (DATABASE.md 3.5):
- user_id     ON DELETE RESTRICT : users are deactivated, never deleted.
- project_id  ON DELETE SET NULL : the entry survives its project; the name is kept in "details".
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.project import Project
from app.models.user import User


class ActivityAction(StrEnum):
    """Every kind of change the log records. The details shape of each is in ARCHITECTURE.md 7.5."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    PROGRESS_LOGGED = "progress_logged"
    PROGRESS_DELETED = "progress_deleted"
    ROLE_CHANGED = "role_changed"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"


class ActivityEntityType(StrEnum):
    """What kind of record entity_id points at."""

    PROJECT = "project"
    PROGRESS_UPDATE = "progress_update"
    USER = "user"


activity_action_enum = Enum(
    ActivityAction,
    name="activity_action",
    values_callable=lambda actions: [action.value for action in actions],
)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_activity_logs_user_id_users", ondelete="RESTRICT")
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", name="fk_activity_logs_project_id_projects", ondelete="SET NULL")
    )
    action: Mapped[ActivityAction] = mapped_column(activity_action_enum)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()
    project: Mapped[Project | None] = relationship()

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.id} action={self.action} {self.entity_type}={self.entity_id}>"


# The organisation-wide feed reads newest first; id breaks ties between rows saved in one transaction.
Index("ix_activity_logs_created", ActivityLog.created_at.desc(), ActivityLog.id.desc())
# "Recent activity" on a project page.
Index("ix_activity_logs_project", ActivityLog.project_id, ActivityLog.created_at.desc())
Index("ix_activity_logs_user", ActivityLog.user_id)
