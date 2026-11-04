"""Tests for password hashing and token helpers."""

from datetime import timedelta

import jwt

from app.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_password_and_is_salted() -> None:
    first_hash = hash_password("Forest2026")
    second_hash = hash_password("Forest2026")

    assert "Forest2026" not in first_hash
    # A random salt means the same password gives a different hash each time.
    assert first_hash != second_hash


def test_correct_password_verifies() -> None:
    assert verify_password("Forest2026", hash_password("Forest2026"))


def test_wrong_password_does_not_verify() -> None:
    assert not verify_password("Forest2027", hash_password("Forest2026"))


def test_password_longer_than_bcrypt_limit_does_not_verify() -> None:
    assert not verify_password("a1" * 50, hash_password("Forest2026"))


def test_token_round_trip_returns_user_id() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_is_rejected() -> None:
    expired_token = create_access_token(42, expires_in=timedelta(seconds=-1))
    assert decode_access_token(expired_token) is None


def test_token_signed_with_other_secret_is_rejected() -> None:
    forged_token = jwt.encode({"sub": "42"}, "attacker-secret-that-is-long-enough!!", algorithm=JWT_ALGORITHM)
    assert decode_access_token(forged_token) is None


def test_garbage_token_is_rejected() -> None:
    assert decode_access_token("not-a-token") is None
