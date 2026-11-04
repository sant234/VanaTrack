"""Tests that every kind of error comes back in the same {detail, code} shape.

No real endpoint accepts input yet, so these tests add tiny routes to a test-only app.
"""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.errors import AppError
from app.main import create_app


class SamplePayload(BaseModel):
    name: str = Field(min_length=3)
    target_value: int = Field(gt=0)


@pytest.fixture
def error_client() -> TestClient:
    application: FastAPI = create_app()

    @application.get("/api/_test/app-error")
    def raise_app_error() -> None:
        raise AppError(status.HTTP_400_BAD_REQUEST, "PROGRESS_NO_CHANGE", "The value did not change.")

    @application.post("/api/_test/validate")
    def validate_payload(payload: SamplePayload) -> SamplePayload:
        return payload

    return TestClient(application)


def test_app_error_returns_consistent_shape(error_client: TestClient) -> None:
    response = error_client.get("/api/_test/app-error")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "The value did not change.", "code": "PROGRESS_NO_CHANGE"}


def test_validation_error_lists_fields(error_client: TestClient) -> None:
    response = error_client.post("/api/_test/validate", json={"name": "ab", "target_value": 0})

    body = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert body["code"] == "VALIDATION_ERROR"
    assert set(body["fields"]) == {"name", "target_value"}
    assert body["detail"]


def test_unknown_route_returns_404_in_standard_shape(error_client: TestClient) -> None:
    response = error_client.get("/api/does-not-exist")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Not Found", "code": "NOT_FOUND"}
