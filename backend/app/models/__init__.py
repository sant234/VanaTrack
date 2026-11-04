"""Import every table model here so Alembic can see all tables."""

from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User, UserRole

__all__ = ["Project", "ProjectStatus", "ProjectType", "User", "UserRole"]
