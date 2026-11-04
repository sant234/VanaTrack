"""Import every table model here so Alembic can see all tables."""

from app.models.progress_update import ProgressUpdate
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User, UserRole

__all__ = ["ProgressUpdate", "Project", "ProjectStatus", "ProjectType", "User", "UserRole"]
