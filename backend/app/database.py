"""Database connection setup: the engine, the session factory, and the model base class."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

# pool_pre_ping checks a connection is still alive before using it.
# Hosted databases (like Neon) close idle connections, and this avoids stale-connection errors.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class for every table model. Alembic reads its metadata to build migrations."""


def get_db() -> Generator[Session, None, None]:
    """Give each request its own database session and always close it afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
