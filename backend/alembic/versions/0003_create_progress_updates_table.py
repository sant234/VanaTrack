"""Create the append-only progress_updates table.

Revision ID: 0003
Revises: 0002

Deletion policy (DATABASE.md 3.5): project_id CASCADE (updates go with their project),
created_by RESTRICT (users are deactivated, never deleted).

The correction rule checks "note IS NOT NULL" explicitly: length(NULL) is NULL, and a CHECK
constraint that evaluates to NULL counts as passed, which would let a correction without a note in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "progress_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("previous_value", sa.Integer(), nullable=False),
        sa.Column("is_correction", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("value >= 0", name="ck_progress_updates_value_non_negative"),
        sa.CheckConstraint("previous_value >= 0", name="ck_progress_updates_previous_non_negative"),
        sa.CheckConstraint(
            "is_correction = false OR (note IS NOT NULL AND char_length(btrim(note)) >= 10)",
            name="ck_progress_updates_correction_needs_note",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_progress_updates_project_id_projects", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_progress_updates_created_by_users", ondelete="RESTRICT"
        ),
    )
    # "Latest update for a project" = first row in this order; the index makes that lookup instant.
    op.create_index(
        "ix_progress_updates_project_latest",
        "progress_updates",
        ["project_id", sa.text("recorded_at DESC"), sa.text("id DESC")],
    )
    op.create_index("ix_progress_updates_created_by", "progress_updates", ["created_by"])


def downgrade() -> None:
    op.drop_table("progress_updates")  # also drops its indexes and constraints
