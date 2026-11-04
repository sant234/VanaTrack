"""Tests for GET /api/health."""

from collections.abc import Generator

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import get_db

# Port 1 on localhost has nothing listening, so connecting fails instantly.
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://nobody:nothing@127.0.0.1:1/missing"


def test_health_returns_ok_when_database_reachable(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_unreachable(app: FastAPI) -> None:
    broken_engine = create_engine(UNREACHABLE_DATABASE_URL)

    def get_broken_db() -> Generator[Session, None, None]:
        session = Session(bind=broken_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = get_broken_db
    response = TestClient(app).get("/api/health")
    broken_engine.dispose()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"status": "degraded", "database": "unreachable"}
