"""Tests for scripts/create_admin.py, including that the password is never printed."""

from contextlib import nullcontext

import pytest
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.security import verify_password
from app.services.auth_service import get_user_by_email
from scripts import create_admin
from tests.conftest import CreateUser

ADMIN_PASSWORD = "Canopy2026"


def _password_must_not_be_requested() -> str:
    raise AssertionError("get_password should not be called for an existing account")


@pytest.fixture
def script_uses_test_db(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    """Point the script's database session at the test database."""
    monkeypatch.setattr(create_admin, "SessionLocal", lambda: nullcontext(db_session))


def test_creates_new_admin(db_session: Session) -> None:
    message = create_admin.create_or_promote_admin(
        db_session, "Root@VanaTrack.demo", "Head Office", lambda: ADMIN_PASSWORD
    )

    admin = get_user_by_email(db_session, "root@vanatrack.demo")
    assert message == "Created admin account root@vanatrack.demo."
    assert admin.role == UserRole.ADMIN
    assert verify_password(ADMIN_PASSWORD, admin.password_hash)


def test_promotes_existing_user_without_changing_password(
    db_session: Session, create_user: CreateUser
) -> None:
    user = create_user(email="lead@vanatrack.demo", role=UserRole.VIEWER, is_active=False)
    original_hash = user.password_hash

    message = create_admin.create_or_promote_admin(
        db_session, "lead@vanatrack.demo", None, _password_must_not_be_requested
    )

    assert "Promoted" in message
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert user.password_hash == original_hash


def test_rejects_invalid_email(db_session: Session) -> None:
    with pytest.raises(create_admin.AdminSetupError, match="valid email"):
        create_admin.create_or_promote_admin(db_session, "nope", "Head Office", lambda: ADMIN_PASSWORD)


def test_requires_name_for_new_account(db_session: Session) -> None:
    with pytest.raises(create_admin.AdminSetupError, match="--name is required"):
        create_admin.create_or_promote_admin(db_session, "new@vanatrack.demo", None, lambda: ADMIN_PASSWORD)


def test_prompt_retries_until_passwords_match(monkeypatch: pytest.MonkeyPatch) -> None:
    typed = iter(["weak", "Canopy2026", "Typo2026", "Canopy2026", "Canopy2026"])
    monkeypatch.setattr(create_admin.getpass, "getpass", lambda _prompt: next(typed))

    assert create_admin.read_password_from_prompt() == "Canopy2026"


def test_prompt_gives_up_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(create_admin.getpass, "getpass", lambda _prompt: "weak")

    with pytest.raises(create_admin.AdminSetupError, match="Too many attempts"):
        create_admin.read_password_from_prompt()


@pytest.mark.usefixtures("script_uses_test_db")
def test_main_with_env_password_never_prints_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], db_session: Session
) -> None:
    monkeypatch.setenv(create_admin.PASSWORD_ENV_VAR, ADMIN_PASSWORD)

    exit_code = create_admin.main(["--email", "ops@vanatrack.demo", "--name", "Ops", "--password-from-env"])

    output = capsys.readouterr()
    assert exit_code == 0
    assert ADMIN_PASSWORD not in output.out + output.err
    assert get_user_by_email(db_session, "ops@vanatrack.demo").role == UserRole.ADMIN


@pytest.mark.usefixtures("script_uses_test_db")
def test_main_with_weak_env_password_fails_without_printing_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], db_session: Session
) -> None:
    monkeypatch.setenv(create_admin.PASSWORD_ENV_VAR, "weakpass")

    exit_code = create_admin.main(["--email", "ops@vanatrack.demo", "--name", "Ops", "--password-from-env"])

    output = capsys.readouterr()
    assert exit_code == 1
    assert "weakpass" not in output.out + output.err
    assert get_user_by_email(db_session, "ops@vanatrack.demo") is None


@pytest.mark.usefixtures("script_uses_test_db")
def test_main_with_missing_env_password_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(create_admin.PASSWORD_ENV_VAR, raising=False)

    exit_code = create_admin.main(["--email", "ops@vanatrack.demo", "--name", "Ops", "--password-from-env"])

    assert exit_code == 1
    assert "ADMIN_PASSWORD is not set" in capsys.readouterr().err


def test_password_flag_does_not_exist() -> None:
    with pytest.raises(SystemExit):
        create_admin.parse_args(["--email", "a@vanatrack.demo", "--password", "Canopy2026"])
