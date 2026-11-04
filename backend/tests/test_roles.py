"""Tests for the require_roles guard, using a test-only route that admins and managers may use."""

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from app.deps import require_roles
from app.models.user import User, UserRole
from tests.conftest import CreateUser, auth_headers

GUARDED_URL = "/api/_test/managers-only"


@pytest.fixture
def guarded_client(app: FastAPI) -> TestClient:
    @app.get(GUARDED_URL)
    def managers_only(user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))) -> dict:
        return {"hello": user.name}

    return TestClient(app)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.MANAGER])
def test_allowed_roles_pass(guarded_client: TestClient, create_user: CreateUser, role: UserRole) -> None:
    user = create_user(role=role, name="Allowed")

    response = guarded_client.get(GUARDED_URL, headers=auth_headers(user))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"hello": "Allowed"}


def test_viewer_is_blocked_with_403(guarded_client: TestClient, create_user: CreateUser) -> None:
    viewer = create_user(role=UserRole.VIEWER)

    response = guarded_client.get(GUARDED_URL, headers=auth_headers(viewer))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "Your role (viewer) cannot perform this action.",
        "code": "INSUFFICIENT_ROLE",
    }


def test_role_guard_still_requires_login(guarded_client: TestClient) -> None:
    response = guarded_client.get(GUARDED_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
