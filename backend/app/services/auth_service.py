"""Business rules for creating accounts and checking logins."""

from functools import lru_cache

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest
from app.security import hash_password, verify_password

# One message for "no such email", "wrong password" and "deactivated", so an attacker
# cannot use the login form to discover which emails have accounts.
INVALID_CREDENTIALS_MESSAGE = "Incorrect email or password."


def normalize_email(email: str) -> str:
    """Emails are case-insensitive in practice, so we always store and compare them in lowercase."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_user(db: Session, data: RegisterRequest) -> User:
    """Create a new viewer account. Raises 409 if the email is already registered."""
    email = normalize_email(data.email)
    if get_user_by_email(db, email):
        raise _email_taken_error()

    user = User(name=data.name, email=email, password_hash=hash_password(data.password), role=UserRole.VIEWER)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        # Two sign-ups with the same email at the same moment: the database's unique rule catches it.
        db.rollback()
        raise _email_taken_error() from error
    db.refresh(user)
    return user


@lru_cache
def _dummy_password_hash() -> str:
    return hash_password("timing-equaliser-not-a-real-password-1")


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Return the user if the email and password match an active account, otherwise raise 401."""
    user = get_user_by_email(db, email)
    if user is None:
        # Still run a hash check so "unknown email" takes as long as "wrong password".
        verify_password(password, _dummy_password_hash())
        raise _invalid_credentials_error()

    if not verify_password(password, user.password_hash) or not user.is_active:
        raise _invalid_credentials_error()
    return user


def _email_taken_error() -> AppError:
    return AppError(
        status.HTTP_409_CONFLICT, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists."
    )


def _invalid_credentials_error() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", INVALID_CREDENTIALS_MESSAGE)
