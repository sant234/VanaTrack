"""Create the projects table and the project_type / project_status enums.

Revision ID: 0002
Revises: 0001

Deletion policy: owner_id uses ON DELETE RESTRICT, so a user who owns projects cannot be deleted
(deactivate them instead). See DATABASE.md, "Deletion policy".
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

project_type = sa.Enum(
    "afforestation", "water_conservation", "solar", "waste_management", "other", name="project_type"
)
project_status = sa.Enum("planned", "active", "on_hold", "completed", "cancelled", name="project_status")


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", project_type, nullable=False),
        sa.Column("status", project_status, server_default="planned", nullable=False),
        sa.Column("target_value", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("state", sa.String(length=60), nullable=False),
        sa.Column("district", sa.String(length=60), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("budget_inr", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_value > 0", name="ck_projects_target_positive"),
        sa.CheckConstraint("end_date >= start_date", name="ck_projects_end_after_start"),
        sa.CheckConstraint("budget_inr IS NULL OR budget_inr >= 0", name="ck_projects_budget_non_negative"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_projects_owner_id_users", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_type", "projects", ["type"])


def downgrade() -> None:
    op.drop_table("projects")  # also drops its indexes and constraints
    # Dropping a table does not remove enum types; remove them so upgrade can run again cleanly.
    bind = op.get_bind()
    project_status.drop(bind, checkfirst=True)
    project_type.drop(bind, checkfirst=True)
