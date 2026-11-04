"""Permission rules as plain functions, shared by the API guards and the can_edit flag in responses."""

from app.models.project import Project
from app.models.user import User, UserRole


def can_edit_project(user: User, project: Project) -> bool:
    """Admins can edit any project; managers only the projects they own.

    The role check matters: an owner who is later demoted to viewer becomes read-only.
    """
    if user.role == UserRole.ADMIN:
        return True
    return user.role == UserRole.MANAGER and project.owner_id == user.id
