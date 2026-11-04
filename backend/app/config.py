"""Application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# HS256 tokens need a secret of at least 32 bytes to be hard to brute-force (RFC 7518 section 3.2).
JWT_SECRET_MIN_LENGTH = 32


class Settings(BaseSettings):
    """All configurable values in one place, so no secret lives in the code."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str | None = None
    # Required, no default: the app refuses to start without a strong secret.
    jwt_secret: str = Field(min_length=JWT_SECRET_MIN_LENGTH)
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"
    # "Today" for schedule maths. The server clock runs on UTC, but the organisation works in India.
    app_timezone: str = "Asia/Kolkata"
    co2_kg_per_tree_per_year: float = 21.0

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS_ORIGINS value into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return one shared Settings object (read from the environment only once)."""
    return Settings()
