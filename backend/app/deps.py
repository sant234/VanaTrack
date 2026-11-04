"""Reusable guards that routes declare with Depends(...).

get_current_user                -> who is calling? (401 if not logged in)
require_roles(..)               -> is their role allowed here? (403 if not)
require_project_owner_or_admin  -> may they change this project? (404 if missing, 403 if not)
"""

from collections.abc import Callable

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models.project import Project
from app.models.user import User, UserRole
from app.permissions import can_edit_project
from app.security import decode_access_token
from app.services.project_service import get_project_or_404

# auto_error=False lets us return our own error shape instead of FastAPI's default one.
bearer_scheme = HTTPBearer(auto_error=False)

# Tells the client which login scheme to use, as the HTTP standard expects with a 401.
BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def _unauthorized(code: str, message: str) -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, code, message, headers=BEARER_CHALLENGE)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Read the Bearer token, check it, and load the user it belongs to."""
    if credentials is None:
        raise _unauthorized("NOT_AUTHENTICATED", "Please log in to continue.")

    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise _unauthorized("INVALID_TOKEN", "Your session is invalid or has expired. Please log in again.")
    if not user.is_active:
        raise _unauthorized("ACCOUNT_DEACTIVATED", "This account has been deactivated.")
    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Build a guard that only lets the given roles through.

    Usage:  current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
    """

    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                status.HTTP_403_FORBIDDEN,
                "INSUFFICIENT_ROLE",
                f"Your role ({current_user.role}) cannot perform this action.",
            )
        return current_user

    return check_role


def require_project_owner_or_admin(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    """Load the project from the URL and allow only its owning manager or an admin to continue."""
    project = get_project_or_404(db, project_id)
    if not can_edit_project(current_user, project):
        raise AppError(
            status.HTTP_403_FORBIDDEN, "NOT_PROJECT_OWNER", "You can only modify projects you own."
        )
    return project
