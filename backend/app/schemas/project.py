"""Shapes of project data going in and out of the API, with all single-field validation rules."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.constants import canonical_state_name
from app.models.project import ProjectStatus, ProjectType

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 150
DESCRIPTION_MAX_LENGTH = 2000
UNIT_MAX_LENGTH = 30
DISTRICT_MAX_LENGTH = 60
TARGET_MAX_VALUE = 1_000_000_000
SEARCH_MAX_LENGTH = 100

ProjectName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
]
TargetValue = Annotated[int, Field(gt=0, le=TARGET_MAX_VALUE, strict=True)]
Unit = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=UNIT_MAX_LENGTH),
]
BudgetInr = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


def _empty_to_none(value: str | None) -> str | None:
    """Treat "" or "   " in an optional text field as "not provided"."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _validate_state(value: str) -> str:
    state = canonical_state_name(value)
    if state is None:
        raise ValueError("Choose a state or union territory from the list.")
    return state


class _ProjectFieldRules(BaseModel):
    """Validators shared by create and update, so both apply exactly the same rules."""

    @field_validator("description", "district", mode="before", check_fields=False)
    @classmethod
    def blank_text_is_none(cls, value: str | None) -> str | None:
        return _empty_to_none(value)

    @field_validator("state", check_fields=False)
    @classmethod
    def state_must_be_known(cls, value: str | None) -> str | None:
        return None if value is None else _validate_state(value)


class ProjectCreate(_ProjectFieldRules):
    name: ProjectName
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    type: ProjectType
    status: ProjectStatus = ProjectStatus.PLANNED
    target_value: TargetValue
    unit: Unit
    state: str
    district: str | None = Field(default=None, max_length=DISTRICT_MAX_LENGTH)
    start_date: date
    end_date: date
    budget_inr: BudgetInr | None = None

    @field_validator("end_date")
    @classmethod
    def end_not_before_start(cls, end_date: date, info: ValidationInfo) -> date:
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("End date cannot be before the start date.")
        return end_date


# Fields that may be left out of an update, but may not be set to null.
REQUIRED_PROJECT_FIELDS = (
    "name",
    "type",
    "status",
    "target_value",
    "unit",
    "state",
    "start_date",
    "end_date",
)


class ProjectUpdate(_ProjectFieldRules):
    """Every field is optional: only the fields sent are changed.

    owner_id is deliberately absent, so ownership can never be changed through an update.
    The end-date-vs-start-date rule is checked in the service, after merging with saved values.
    """

    name: ProjectName | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    type: ProjectType | None = None
    status: ProjectStatus | None = None
    target_value: TargetValue | None = None
    unit: Unit | None = None
    state: str | None = None
    district: str | None = Field(default=None, max_length=DISTRICT_MAX_LENGTH)
    start_date: date | None = None
    end_date: date | None = None
    budget_inr: BudgetInr | None = None

    @field_validator(*REQUIRED_PROJECT_FIELDS, mode="before")
    @classmethod
    def required_fields_cannot_be_cleared(cls, value: object) -> object:
        # Only runs when the client actually sent the field, so leaving it out is still fine.
        if value is None:
            raise ValueError("This field cannot be empty.")
        return value


class ProjectSort(StrEnum):
    NAME = "name"
    CREATED_AT = "created_at"
    END_DATE = "end_date"
    PROGRESS = "progress"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class ProjectListParams(BaseModel):
    """Query parameters for GET /projects. All optional and combinable."""

    model_config = ConfigDict(extra="forbid")

    search: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    type: ProjectType | None = None
    status: ProjectStatus | None = None
    state: str | None = None
    mine: bool = False
    sort: ProjectSort = ProjectSort.CREATED_AT
    order: SortOrder = SortOrder.DESC

    @field_validator("search", mode="before")
    @classmethod
    def blank_search_is_none(cls, value: str | None) -> str | None:
        return _empty_to_none(value)

    @field_validator("state")
    @classmethod
    def state_must_be_known(cls, value: str | None) -> str | None:
        return None if value is None else _validate_state(value)


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# Money is stored exactly (Decimal) but sent as a plain JSON number, which the browser can use directly.
MoneyOut = Annotated[Decimal, PlainSerializer(float, return_type=float)]


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    type: ProjectType
    status: ProjectStatus
    target_value: int
    unit: str
    state: str
    district: str | None
    start_date: date
    end_date: date
    budget_inr: MoneyOut | None
    owner: OwnerOut
    created_at: datetime
    updated_at: datetime
    # Derived values: calculated on every request, never stored (see services/progress_service.py).
    current_value: int
    progress_percent: float
    expected_percent: float
    is_behind_schedule: bool
    last_updated_at: datetime | None
    # Whether the user who asked may edit or delete this project.
    can_edit: bool


class OptionOut(BaseModel):
    value: str
    label: str


class ProjectOptions(BaseModel):
    types: list[OptionOut]
    statuses: list[OptionOut]
    states: list[str]
