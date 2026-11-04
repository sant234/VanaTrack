"""Shared pytest setup.

How test isolation works:
1. Once per test run, the TEST database is wiped and rebuilt by running all Alembic migrations.
   (This also proves our migrations work from scratch.)
2. Each test runs inside a database transaction that is rolled back afterwards,
   so no test can see data left behind by another test.
"""

from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.main import create_app


def _test_database_url() -> str:
    url = get_settings().test_database_url
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not set. Copy backend/.env.example to backend/.env.")
    if url == get_settings().database_url:
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL, or tests would wipe real data.")
    return url


def _reset_schema_and_migrate(engine: Engine, database_url: str) -> None:
    """Drop everything in the test database, then rebuild it with Alembic migrations."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    alembic_config = Config("alembic.ini")
    alembic_config.attributes["database_url"] = database_url
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    engine = create_engine(database_url)
    _reset_schema_and_migrate(engine, database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """A session whose changes are always rolled back when the test ends."""
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    # "create_savepoint" means a commit() inside app code only commits a savepoint,
    # so the outer transaction can still undo everything.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def app(db_session: Session) -> FastAPI:
    """A fresh app instance whose database dependency points at the test session."""
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
