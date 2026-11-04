"""The users table: everyone who can log in, and what role they have."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(StrEnum):
    """What a user is allowed to do. See ARCHITECTURE.md section 7.4."""

    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


# Stored as a PostgreSQL enum named "user_role" holding the lowercase values above.
user_role_enum = Enum(
    UserRole,
    name="user_role",
    values_callable=lambda roles: [role.value for role in roles],
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(user_role_enum, default=UserRole.VIEWER, server_default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        # Deliberately leaves out password_hash so it never ends up in logs.
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
