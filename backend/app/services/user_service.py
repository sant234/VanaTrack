"""Business rules for user management (admins only): list users, change a role, (de)activate.

Each real change writes one activity entry in the same transaction (ARCHITECTURE.md 7.5).
An admin may not change their own role or deactivate themselves, so the last admin can never lock
everyone out by accident.
"""

from fastapi import status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.activity_log import ActivityAction, ActivityEntityType
from app.models.project import Project
from app.models.user import User
from app.schemas.user import UserAdminOut, UserAdminUpdate
from app.services.activity_service import record_activity


def _users_with_project_counts() -> Select:
    """Every user with the number of projects they own (0 for none, thanks to the outer join)."""
    owned_project_count = func.count(Project.id).label("owned_project_count")
    return select(User, owned_project_count).outerjoin(Project, Project.owner_id == User.id).group_by(User.id)


def _to_out(user: User, owned_project_count: int) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        owned_project_count=owned_project_count,
    )


def list_users(db: Session) -> list[UserAdminOut]:
    """Sorted by name; id breaks ties so two people with the same name keep a stable order."""
    query = _users_with_project_counts().order_by(User.name, User.id)
    return [_to_out(row.User, row.owned_project_count) for row in db.execute(query)]


def get_user_out(db: Session, user_id: int) -> UserAdminOut:
    row = db.execute(_users_with_project_counts().where(User.id == user_id)).one()
    return _to_out(row.User, row.owned_project_count)


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "User not found.")
    return user


def _cannot_modify_self(message: str) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, "CANNOT_MODIFY_SELF", message)


def update_user(db: Session, target: User, data: UserAdminUpdate, admin: User) -> User:
    """Apply only real changes, each with its own activity entry, all in one commit.

    Sending a value equal to the saved one is not a change: nothing is written and nothing is logged.
    """
    sent = data.model_dump(exclude_unset=True)
    role_changes = "role" in sent and sent["role"] != target.role
    active_changes = "is_active" in sent and sent["is_active"] != target.is_active

    if target.id == admin.id:
        if role_changes:
            raise _cannot_modify_self("You cannot change your own role. Ask another admin.")
        if active_changes and not sent["is_active"]:
            raise _cannot_modify_self("You cannot deactivate your own account. Ask another admin.")

    if role_changes:
        record_activity(
            db,
            admin,
            ActivityAction.ROLE_CHANGED,
            ActivityEntityType.USER,
            target.id,
            None,
            {"email": target.email, "from": target.role.value, "to": sent["role"].value},
        )
        target.role = sent["role"]
    if active_changes:
        action = ActivityAction.USER_ACTIVATED if sent["is_active"] else ActivityAction.USER_DEACTIVATED
        record_activity(db, admin, action, ActivityEntityType.USER, target.id, None, {"email": target.email})
        target.is_active = sent["is_active"]

    if role_changes or active_changes:
        db.commit()  # the user change and its activity entries are saved together
    return target
