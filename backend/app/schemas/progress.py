"""Shapes of progress-update data going in and out of the API."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.models.progress_update import CORRECTION_NOTE_MIN_LENGTH

NOTE_MAX_LENGTH = 1000
# progress_updates.value is a PostgreSQL INTEGER (max 2,147,483,647); stay safely below it.
PROGRESS_MAX_VALUE = 2_000_000_000
# Browser and server clocks rarely agree to the second, so allow a small difference.
CLOCK_SKEW_ALLOWANCE = timedelta(minutes=1)

ProgressValue = Annotated[int, Field(ge=0, le=PROGRESS_MAX_VALUE, strict=True)]


class ProgressCreate(BaseModel):
    """A new running total, e.g. {"value": 850} meaning "850 trees planted so far".

    previous_value is never accepted from the client: the server works it out.
    Field order matters: "note" is checked after "is_correction", so its rule can read it.
    """

    value: ProgressValue
    # Must include a timezone (e.g. "2026-11-04T10:00:00+05:30"). Leave out to mean "now".
    recorded_at: AwareDatetime | None = None
    is_correction: bool = False
    # validate_default: run the note rule even when no note was sent (a correction still needs one).
    note: str | None = Field(default=None, max_length=NOTE_MAX_LENGTH, validate_default=True)

    @field_validator("recorded_at")
    @classmethod
    def not_in_the_future(cls, recorded_at: datetime | None) -> datetime | None:
        if recorded_at is not None and recorded_at > datetime.now(UTC) + CLOCK_SKEW_ALLOWANCE:
            raise ValueError("The date cannot be in the future.")
        return recorded_at

    @field_validator("note", mode="before")
    @classmethod
    def blank_note_is_none(cls, note: str | None) -> str | None:
        if note is None:
            return None
        return note.strip() or None

    @field_validator("note")
    @classmethod
    def correction_needs_reason(cls, note: str | None, info: ValidationInfo) -> str | None:
        if info.data.get("is_correction") and len(note or "") < CORRECTION_NOTE_MIN_LENGTH:
            raise ValueError(f"Explain the correction in at least {CORRECTION_NOTE_MIN_LENGTH} characters.")
        return note


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProgressUpdateOut(BaseModel):
    id: int
    value: int
    previous_value: int
    change: int  # value - previous_value, e.g. +250 or -150
    is_correction: bool
    note: str | None
    recorded_at: datetime
    created_at: datetime
    author: AuthorOut
    # Whether the user who asked may delete this entry (admins, newest entry only).
    can_delete: bool
