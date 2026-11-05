"""Create the append-only activity_logs table and the activity_action enum.

Revision ID: 0004
Revises: 0003

Deletion policy (DATABASE.md 3.5): user_id RESTRICT (users are deactivated, never deleted),
project_id SET NULL (the entry outlives its project; the project name is kept in "details").
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

activity_action = sa.Enum(
    "created",
    "updated",
    "deleted",
    "progress_logged",
    "progress_deleted",
    "role_changed",
    "user_deactivated",
    "user_activated",
    name="activity_action",
)


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("action", activity_action, nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_activity_logs_user_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_activity_logs_project_id_projects", ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_activity_logs_created", "activity_logs", [sa.text("created_at DESC"), sa.text("id DESC")]
    )
    op.create_index("ix_activity_logs_project", "activity_logs", ["project_id", sa.text("created_at DESC")])
    op.create_index("ix_activity_logs_user", "activity_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("activity_logs")  # also drops its indexes and constraints
    # Dropping a table does not remove enum types; remove it so upgrade can run again cleanly.
    activity_action.drop(op.get_bind(), checkfirst=True)
