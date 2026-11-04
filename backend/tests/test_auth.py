"""Tests for POST /api/auth/register, POST /api/auth/login and GET /api/auth/me."""

from datetime import timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.security import create_access_token
from tests.conftest import DEFAULT_TEST_PASSWORD, CreateUser, auth_headers

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"

VALID_SIGNUP = {"name": "Asha Rao", "email": "asha@vanatrack.demo", "password": "Saplings42"}


# ---------- register ----------


def test_register_creates_viewer_account(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json=VALID_SIGNUP)

    body = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert body["email"] == "asha@vanatrack.demo"
    assert body["name"] == "Asha Rao"
    assert body["role"] == "viewer"
    assert body["is_active"] is True


def test_register_stores_email_in_lowercase_and_trims_name(client: TestClient) -> None:
    response = client.post(
        REGISTER_URL, json={**VALID_SIGNUP, "email": "Asha@VanaTrack.DEMO", "name": " Asha "}
    )

    assert response.json()["email"] == "asha@vanatrack.demo"
    assert response.json()["name"] == "Asha"


def test_register_ignores_requested_role(client: TestClient, db_session: Session) -> None:
    response = client.post(REGISTER_URL, json={**VALID_SIGNUP, "role": "admin"})

    assert response.json()["role"] == "viewer"
    assert db_session.get(User, response.json()["id"]).role == UserRole.VIEWER


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    client.post(REGISTER_URL, json=VALID_SIGNUP)
    response = client.post(REGISTER_URL, json=VALID_SIGNUP)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_duplicate_email_with_different_case_returns_409(client: TestClient) -> None:
    client.post(REGISTER_URL, json=VALID_SIGNUP)
    response = client.post(REGISTER_URL, json={**VALID_SIGNUP, "email": "ASHA@vanatrack.demo"})

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    ("password", "expected_message_part"),
    [
        ("short1", "at least 8"),
        ("onlyletters", "number"),
        ("12345678", "letter"),
        ("a1" * 40, "at most 72"),
    ],
)
def test_register_weak_password_returns_422(
    client: TestClient, password: str, expected_message_part: str
) -> None:
    response = client.post(REGISTER_URL, json={**VALID_SIGNUP, "password": password})

    body = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert body["code"] == "VALIDATION_ERROR"
    assert expected_message_part in body["fields"]["password"]


def test_register_invalid_email_returns_422(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json={**VALID_SIGNUP, "email": "not-an-email"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "email" in response.json()["fields"]


def test_register_blank_name_returns_422(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json={**VALID_SIGNUP, "name": "   "})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "name" in response.json()["fields"]


def test_register_never_returns_password_or_hash(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json=VALID_SIGNUP)

    assert "password" not in response.text
    assert VALID_SIGNUP["password"] not in response.text
    assert "$2b$" not in response.text


# ---------- login ----------


def test_login_returns_token_and_user(client: TestClient, create_user: CreateUser) -> None:
    user = create_user(email="ravi@vanatrack.demo", role=UserRole.MANAGER)

    response = client.post(
        LOGIN_URL, json={"email": "ravi@vanatrack.demo", "password": DEFAULT_TEST_PASSWORD}
    )

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["id"] == user.id
    assert body["user"]["role"] == "manager"
    assert "password" not in response.text


def test_login_token_works_on_me(client: TestClient, create_user: CreateUser) -> None:
    create_user(email="ravi@vanatrack.demo")
    token = client.post(
        LOGIN_URL, json={"email": "ravi@vanatrack.demo", "password": DEFAULT_TEST_PASSWORD}
    ).json()["access_token"]

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "ravi@vanatrack.demo"


def test_login_email_is_case_insensitive(client: TestClient, create_user: CreateUser) -> None:
    create_user(email="ravi@vanatrack.demo")

    response = client.post(
        LOGIN_URL, json={"email": "RAVI@VanaTrack.demo", "password": DEFAULT_TEST_PASSWORD}
    )

    assert response.status_code == status.HTTP_200_OK


def test_login_wrong_password_returns_401(client: TestClient, create_user: CreateUser) -> None:
    create_user(email="ravi@vanatrack.demo")

    response = client.post(LOGIN_URL, json={"email": "ravi@vanatrack.demo", "password": "WrongPass99"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Incorrect email or password.", "code": "INVALID_CREDENTIALS"}


def test_login_unknown_email_gives_same_error_as_wrong_password(
    client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="ravi@vanatrack.demo")

    wrong_password = client.post(LOGIN_URL, json={"email": "ravi@vanatrack.demo", "password": "WrongPass99"})
    unknown_email = client.post(LOGIN_URL, json={"email": "nobody@vanatrack.demo", "password": "WrongPass99"})

    assert unknown_email.status_code == status.HTTP_401_UNAUTHORIZED
    assert unknown_email.json() == wrong_password.json()


def test_login_inactive_user_returns_401_with_same_message(
    client: TestClient, create_user: CreateUser
) -> None:
    create_user(email="gone@vanatrack.demo", is_active=False)

    response = client.post(
        LOGIN_URL, json={"email": "gone@vanatrack.demo", "password": DEFAULT_TEST_PASSWORD}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_login_missing_fields_returns_422(client: TestClient) -> None:
    response = client.post(LOGIN_URL, json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert set(response.json()["fields"]) == {"email", "password"}


# ---------- me ----------


def test_me_with_valid_token_returns_user(client: TestClient, create_user: CreateUser) -> None:
    user = create_user(email="meera@vanatrack.demo", role=UserRole.ADMIN)

    response = client.get(ME_URL, headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "meera@vanatrack.demo"
    assert response.json()["role"] == "admin"
    assert "password" not in response.text


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "NOT_AUTHENTICATED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_with_garbage_token_returns_401(client: TestClient) -> None:
    response = client.get(ME_URL, headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "INVALID_TOKEN"


def test_me_with_expired_token_returns_401(client: TestClient, create_user: CreateUser) -> None:
    user = create_user()
    expired_token = create_access_token(user.id, expires_in=timedelta(seconds=-1))

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "INVALID_TOKEN"


def test_me_with_token_for_deleted_user_returns_401(client: TestClient, create_user: CreateUser) -> None:
    missing_user_id = 999_999
    token = create_access_token(missing_user_id)

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "INVALID_TOKEN"


def test_me_after_account_deactivated_returns_401(
    client: TestClient, create_user: CreateUser, db_session: Session
) -> None:
    user = create_user()
    headers = auth_headers(user)  # logged in while still active
    user.is_active = False
    db_session.commit()

    response = client.get(ME_URL, headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "ACCOUNT_DEACTIVATED"
