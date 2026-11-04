"""Shapes of the data going in and out of the auth endpoints.

Pydantic checks every incoming request against these classes and rejects bad input with a 422
before our code ever runs. Response classes control exactly which fields leave the server.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.security import BCRYPT_MAX_PASSWORD_BYTES

PASSWORD_MIN_LENGTH = 8
NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 100
LOGIN_PASSWORD_MAX_LENGTH = 200


def find_password_problem(password: str) -> str | None:
    """Return why a new password is not acceptable, or None if it is fine.

    Shared by the register endpoint and the create_admin script so the rules never drift apart.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if len(password.encode()) > BCRYPT_MAX_PASSWORD_BYTES:
        return f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} characters."
    if not any(character.isalpha() for character in password):
        return "Password must contain at least one letter."
    if not any(character.isdigit() for character in password):
        return "Password must contain at least one number."
    return None


class RegisterRequest(BaseModel):
    """Sign-up form. Any extra field (such as "role") is ignored: new accounts are always viewers."""

    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def strip_name(cls, name: str) -> str:
        stripped = name.strip()
        if len(stripped) < NAME_MIN_LENGTH:
            raise ValueError(f"Name must be at least {NAME_MIN_LENGTH} characters.")
        return stripped

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, password: str) -> str:
        problem = find_password_problem(password)
        if problem:
            raise ValueError(problem)
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    # No strength rules here: we only compare against the stored hash.
    password: str = Field(min_length=1, max_length=LOGIN_PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    """A user as the API returns it. There is no password field, so the hash can never leak."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
