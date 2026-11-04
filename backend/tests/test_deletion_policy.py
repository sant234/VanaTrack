"""Guards for the deletion policy (DATABASE.md, "Deletion policy").

These tests read the REAL database structure, so they automatically cover every table that
later migrations add (progress updates, activity log, ...). If a new foreign key forgets to choose
an ON DELETE rule, or a project delete leaves rows pointing at a missing project, a test fails.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import UserRole
from tests.conftest import CreateProject, CreateUser, auth_headers

# PostgreSQL's codes for ON DELETE rules (pg_constraint.confdeltype).
NO_ACTION = "a"
RESTRICT = "r"
CASCADE = "c"
SET_NULL = "n"

ALL_FOREIGN_KEYS_SQL = text(
    """
    SELECT conrelid::regclass::text AS table_name,
           conname                  AS constraint_name,
           confrelid::regclass::text AS references_table,
           confdeltype              AS delete_rule,
           (SELECT attname FROM pg_attribute
             WHERE attrelid = conrelid AND attnum = conkey[1]) AS column_name
    FROM pg_constraint
    WHERE contype = 'f' AND connamespace = 'public'::regnamespace
    """
)


def _foreign_keys(db_session: Session) -> list:
    return list(db_session.execute(ALL_FOREIGN_KEYS_SQL))


def test_every_foreign_key_declares_an_explicit_delete_rule(db_session: Session) -> None:
    """PostgreSQL's default (NO ACTION) is never chosen on purpose, so it is not allowed."""
    implicit = [fk.constraint_name for fk in _foreign_keys(db_session) if fk.delete_rule == NO_ACTION]
    assert implicit == [], f"Foreign keys without an explicit ON DELETE rule: {implicit}"


def test_rows_pointing_at_a_project_are_deleted_or_unlinked_with_it(db_session: Session) -> None:
    """Child records CASCADE (deleted with the project); history records SET NULL (kept, unlinked)."""
    wrong = [
        fk.constraint_name
        for fk in _foreign_keys(db_session)
        if fk.references_table == "projects" and fk.delete_rule not in (CASCADE, SET_NULL)
    ]
    assert wrong == [], f"Foreign keys to projects must be CASCADE or SET NULL: {wrong}"


def test_project_owner_link_restricts_user_deletion(db_session: Session) -> None:
    owner_fk = next(
        fk for fk in _foreign_keys(db_session) if fk.constraint_name == "fk_projects_owner_id_users"
    )
    assert owner_fk.delete_rule == RESTRICT


def test_user_who_owns_projects_cannot_be_deleted(
    db_session: Session, create_user: CreateUser, create_project: CreateProject
) -> None:
    owner = create_user(role=UserRole.MANAGER)
    create_project(owner)

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": owner.id})


def test_deleting_a_project_leaves_no_rows_pointing_at_it(
    client, db_session: Session, create_user: CreateUser, create_project: CreateProject
) -> None:
    """After a delete, no table may still reference the deleted project id."""
    owner = create_user(role=UserRole.MANAGER)
    project_id = create_project(owner).id

    response = client.delete(f"/api/projects/{project_id}", headers=auth_headers(owner))

    assert response.status_code == 204
    assert db_session.get(Project, project_id) is None
    for fk in _foreign_keys(db_session):
        if fk.references_table != "projects":
            continue
        count_sql = text(f'SELECT count(*) FROM "{fk.table_name}" WHERE "{fk.column_name}" = :id')
        leftover = db_session.execute(count_sql, {"id": project_id}).scalar_one()
        assert leftover == 0, f"{fk.table_name}.{fk.column_name} still points at deleted project"


def test_guard_catches_a_foreign_key_that_forgets_its_delete_rule(db_session: Session) -> None:
    """Prove the guards above really fail on the mistake they exist to catch.

    PostgreSQL can undo table creation inside a transaction, so the probe table is rolled back afterwards.
    """
    savepoint = db_session.begin_nested()
    db_session.execute(
        text("CREATE TABLE guard_probe (id serial PRIMARY KEY, project_id int REFERENCES projects(id))")
    )
    probe_keys = [fk for fk in _foreign_keys(db_session) if fk.table_name == "guard_probe"]
    savepoint.rollback()

    assert len(probe_keys) == 1
    assert probe_keys[0].delete_rule == NO_ACTION  # the default the guards reject
