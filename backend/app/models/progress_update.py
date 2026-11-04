"""The progress_updates table: an append-only log of a project's running total.

Each row records the NEW cumulative total (e.g. "850 trees planted so far") and the total just
before it (previous_value), so the history reads "600 -> 850 (+250)".
Rows are never edited. A wrong number is fixed by adding a correction entry.

Deletion policy (DATABASE.md 3.5):
- project_id  ON DELETE CASCADE  : updates are meaningless without their project.
- created_by  ON DELETE RESTRICT : users are deactivated, never deleted.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User

CORRECTION_NOTE_MIN_LENGTH = 10


class ProgressUpdate(Base):
    __tablename__ = "progress_updates"
    __table_args__ = (
        CheckConstraint("value >= 0", name="ck_progress_updates_value_non_negative"),
        CheckConstraint("previous_value >= 0", name="ck_progress_updates_previous_non_negative"),
        # "note IS NOT NULL" matters: length(NULL) is NULL, and a CHECK that evaluates to NULL passes.
        CheckConstraint(
            "is_correction = false OR "
            f"(note IS NOT NULL AND char_length(btrim(note)) >= {CORRECTION_NOTE_MIN_LENGTH})",
            name="ck_progress_updates_correction_needs_note",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", name="fk_progress_updates_project_id_projects", ondelete="CASCADE")
    )
    value: Mapped[int] = mapped_column(Integer)
    previous_value: Mapped[int] = mapped_column(Integer)
    is_correction: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    note: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_progress_updates_created_by_users", ondelete="RESTRICT"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return (
            f"<ProgressUpdate id={self.id} project_id={self.project_id} {self.previous_value}->{self.value}>"
        )


# "Latest update for a project" is the first row in this order, so this index makes that lookup instant.
Index(
    "ix_progress_updates_project_latest",
    ProgressUpdate.project_id,
    ProgressUpdate.recorded_at.desc(),
    ProgressUpdate.id.desc(),
)
