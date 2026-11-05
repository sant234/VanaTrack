"""Shapes of user-management data going in and out of the admin API."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.user import UserRole


class UserAdminOut(BaseModel):
    """One row of the Users page."""

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    # Counted on every request from the projects table, never stored.
    owned_project_count: int


class UserAdminUpdate(BaseModel):
    """Both fields are optional: only the fields sent are changed. An empty body changes nothing."""

    role: UserRole | None = None
    # strict: only a real JSON true/false is accepted, not "yes" or 1.
    is_active: bool | None = Field(default=None, strict=True)

    @field_validator("role", "is_active", mode="before")
    @classmethod
    def cannot_be_cleared(cls, value: object) -> object:
        # Only runs when the client actually sent the field, so leaving it out is still fine.
        if value is None:
            raise ValueError("This field cannot be empty.")
        return value
