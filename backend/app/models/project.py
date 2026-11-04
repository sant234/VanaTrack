"""The projects table: one environmental project with a target, a place, and a timeline.

Deletion policy (see DATABASE.md, "Deletion policy"):
- A project's owner cannot be deleted while they own projects (ON DELETE RESTRICT).
  Users are deactivated instead of deleted.
- Records that belong to a project (progress updates, Prompt 3) are deleted with it (ON DELETE CASCADE).
- History records that mention a project (activity log, Prompt 5) are kept with the link cleared
  (ON DELETE SET NULL).
The database enforces these rules, so no code path can leave orphaned rows behind.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User


class ProjectType(StrEnum):
    AFFORESTATION = "afforestation"
    WATER_CONSERVATION = "water_conservation"
    SOLAR = "solar"
    WASTE_MANAGEMENT = "waste_management"
    OTHER = "other"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


project_type_enum = Enum(ProjectType, name="project_type", values_callable=_values)
project_status_enum = Enum(ProjectStatus, name="project_status", values_callable=_values)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("target_value > 0", name="ck_projects_target_positive"),
        CheckConstraint("end_date >= start_date", name="ck_projects_end_after_start"),
        CheckConstraint("budget_inr IS NULL OR budget_inr >= 0", name="ck_projects_budget_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[ProjectType] = mapped_column(project_type_enum, index=True)
    status: Mapped[ProjectStatus] = mapped_column(
        project_status_enum, default=ProjectStatus.PLANNED, server_default="planned", index=True
    )
    target_value: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(60))
    district: Mapped[str | None] = mapped_column(String(60))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    budget_inr: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_projects_owner_id_users", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} owner_id={self.owner_id}>"
