"""Alembic migration runner, wired to our app's settings and table models."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (imported so every table model registers itself on Base.metadata)
from app.config import get_settings
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compares this metadata with the real database to generate migrations.
target_metadata = Base.metadata


def get_database_url() -> str:
    """Use a URL passed in by code (e.g. tests), otherwise the app's DATABASE_URL."""
    return config.attributes.get("database_url") or get_settings().database_url


def run_migrations_offline() -> None:
    """Generate SQL without connecting to a database (`alembic upgrade head --sql`)."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply migrations directly."""
    engine = create_engine(get_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
