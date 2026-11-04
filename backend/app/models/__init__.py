"""Import every table model here so Alembic can see all tables."""

from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
