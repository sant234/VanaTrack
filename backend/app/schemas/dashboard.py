"""Shapes of the dashboard responses. Every figure is calculated per request; nothing is stored."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.models.project import ProjectStatus, ProjectType


class DashboardParams(BaseModel):
    """Optional filter shared by every dashboard endpoint, e.g. ?type=afforestation."""

    model_config = ConfigDict(extra="forbid")

    type: ProjectType | None = None


class DashboardSummary(BaseModel):
    total_projects: int
    active_projects: int
    # Average of each counted project's completion % (capped at 100). Counted = started and not cancelled.
    average_completion_percent: float
    completion_project_count: int
    # Sum of current values of projects measured in trees (unit compared case-insensitively).
    trees_planted: int
    # Estimate only: trees_planted x CO2_KG_PER_TREE_PER_YEAR, in tonnes per year.
    estimated_co2_tonnes_per_year: float
    co2_kg_per_tree_per_year: float
    behind_schedule_count: int
    exceeded_target_count: int
    needs_attention_count: int


class TypeBreakdown(BaseModel):
    type: ProjectType
    label: str
    project_count: int
    average_completion_percent: float | None  # None when no project of this type counts yet


class StateBreakdown(BaseModel):
    state: str
    project_count: int
    average_completion_percent: float | None
    trees_planted: int


class TrendPoint(BaseModel):
    month: str  # "2026-11"
    average_completion_percent: float | None  # None when no project had started by then
    project_count: int


class AttentionReason(StrEnum):
    BEHIND_SCHEDULE = "behind_schedule"
    NO_RECENT_UPDATE = "no_recent_update"


class AttentionItem(BaseModel):
    id: int
    name: str
    type: ProjectType
    status: ProjectStatus
    owner_name: str
    progress_percent: float
    expected_percent: float
    last_updated_at: datetime | None
    days_since_update: int | None  # None when progress was never logged
    reasons: list[AttentionReason]
