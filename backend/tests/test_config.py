"""Tests for application settings: the documented variables and the startup safety checks."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import JWT_SECRET_MIN_LENGTH, Settings

ENV_EXAMPLE_PATH = Path(__file__).resolve().parent.parent / ".env.example"


def _variables_in_env_example() -> set[str]:
    """Names assigned in .env.example, e.g. "DATABASE_URL" from "DATABASE_URL=...". Comments are skipped."""
    lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    return {
        line.split("=", 1)[0].strip() for line in lines if "=" in line and not line.lstrip().startswith("#")
    }


def test_env_example_lists_every_setting() -> None:
    expected = {field_name.upper() for field_name in Settings.model_fields}

    assert _variables_in_env_example() == expected


def test_short_jwt_secret_refuses_to_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "x" * (JWT_SECRET_MIN_LENGTH - 1))

    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings()
