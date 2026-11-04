"""Create an admin account, or promote an existing account to admin.

Sign-up always creates viewers, so this is how the first admin is made.

Usage (run from the backend/ folder):
    python -m scripts.create_admin --email admin@example.com --name "Head Office"
        -> asks for the password at a hidden prompt (typed twice)

    ADMIN_PASSWORD='...' python -m scripts.create_admin --email admin@example.com --name "Head Office" \
        --password-from-env
        -> for servers with no keyboard (e.g. a Render shell)

Security: there is deliberately no --password option, because command-line arguments are saved in
shell history and visible to other users via `ps`. The password is never printed or logged.
"""

import argparse
import getpass
import os
import sys
from collections.abc import Callable

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.schemas.auth import find_password_problem
from app.security import hash_password
from app.services.auth_service import get_user_by_email, normalize_email

PASSWORD_ENV_VAR = "ADMIN_PASSWORD"
MAX_PROMPT_ATTEMPTS = 3


class AdminSetupError(Exception):
    """A problem the person running the script can fix (bad email, weak password, ...)."""


def validated_password(password: str) -> str:
    problem = find_password_problem(password)
    if problem:
        raise AdminSetupError(problem)
    return password


def read_password_from_prompt() -> str:
    """Ask twice at a hidden prompt (nothing is shown while typing)."""
    for _attempt in range(MAX_PROMPT_ATTEMPTS):
        password = getpass.getpass("Admin password: ")
        problem = find_password_problem(password)
        if problem:
            print(f"  {problem} Try again.")
            continue
        if getpass.getpass("Repeat password: ") != password:
            print("  Passwords did not match. Try again.")
            continue
        return password
    raise AdminSetupError("Too many attempts. No changes were made.")


def read_password_from_env() -> str:
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        raise AdminSetupError(f"{PASSWORD_ENV_VAR} is not set.")
    return validated_password(password)


def create_or_promote_admin(
    db: Session, email: str, name: str | None, get_password: Callable[[], str]
) -> str:
    """Make sure an active admin with this email exists. Returns a summary safe to print.

    get_password is only called when a new account is created; an existing account keeps its password.
    """
    try:
        email = normalize_email(TypeAdapter(EmailStr).validate_python(email))
    except ValidationError as error:
        raise AdminSetupError("That is not a valid email address.") from error

    existing_user = get_user_by_email(db, email)
    if existing_user:
        existing_user.role = UserRole.ADMIN
        existing_user.is_active = True
        db.commit()
        return f"Promoted existing account {email} to admin (password unchanged)."

    if not name or len(name.strip()) < 2:
        raise AdminSetupError("--name is required (at least 2 characters) when creating a new account.")

    admin = User(
        name=name.strip(), email=email, password_hash=hash_password(get_password()), role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()
    return f"Created admin account {email}."


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    # allow_abbrev=False: otherwise "--password" would silently be read as "--password-from-env".
    parser = argparse.ArgumentParser(
        description="Create or promote a VanaTrack admin account.", allow_abbrev=False
    )
    parser.add_argument("--email", required=True, help="Email of the admin account.")
    parser.add_argument("--name", help="Display name (required when creating a new account).")
    parser.add_argument(
        "--password-from-env",
        action="store_true",
        help=f"Read the password from the {PASSWORD_ENV_VAR} environment variable instead of prompting.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    get_password = read_password_from_env if args.password_from_env else read_password_from_prompt
    with SessionLocal() as db:
        try:
            print(create_or_promote_admin(db, args.email, args.name, get_password))
        except AdminSetupError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
