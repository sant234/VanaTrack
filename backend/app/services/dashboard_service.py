"""Dashboard figures, calculated on every request from the same data the project pages use.

How it works:
1. load_snapshots() runs the SAME query as the project list (progress_service.select_projects_with_progress)
   and applies the SAME rules (build_progress), so the dashboard can never disagree with a project page.
2. The small functions below aggregate those snapshots into each widget's numbers.

Why completion is an average of percentages, not "sum achieved / sum target":
projects are measured in different units (trees, kW, kL water ...). Adding 850 trees to 50 kW gives a
meaningless number. Each project's completion % is unit-free, so averaging those is meaningful.
Each project counts at most 100%, so one over-achiever cannot hide projects that are behind.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.progress_update import ProgressUpdate
from app.models.project import Project, ProjectStatus, ProjectType
from app.schemas.dashboard import (
    AttentionItem,
    AttentionReason,
    DashboardSummary,
    StateBreakdown,
    TrendPoint,
    TypeBreakdown,
)
from app.services.progress_service import (
    PERCENT,
    PERCENT_DECIMALS,
    ProjectProgress,
    build_progress,
    select_projects_with_progress,
    today_in_app_timezone,
)

COMPLETION_CAP_PERCENT = 100
TREE_UNIT = "trees"
KG_PER_TONNE = 1000
STALE_AFTER_DAYS = 30
TREND_MONTHS = 12


@dataclass(frozen=True)
class ProjectSnapshot:
    project: Project
    progress: ProjectProgress


# ---------- loading ----------


def load_snapshots(db: Session, project_type: ProjectType | None, today: date) -> list[ProjectSnapshot]:
    """Every project (optionally of one type) with its derived figures, exactly as the list shows them."""
    query, _columns = select_projects_with_progress()
    if project_type is not None:
        query = query.where(Project.type == project_type)
    return [
        ProjectSnapshot(
            row.Project,
            build_progress(row.Project, row.current_value, row.progress_percent, row.last_updated_at, today),
        )
        for row in db.execute(query)
    ]


# ---------- shared rules ----------


def counts_toward_completion(project: Project, as_of: date) -> bool:
    """Cancelled projects are left out: they will never finish, so they would drag every average down.
    Projects that have not started yet are left out too: 0% is expected for them, not a shortfall.
    """
    return project.status != ProjectStatus.CANCELLED and project.start_date <= as_of


def capped_percent(value: int, target: int) -> float:
    return min(value * PERCENT / target, COMPLETION_CAP_PERCENT)


def average_completion(percentages: list[float]) -> float | None:
    return round(mean(percentages), PERCENT_DECIMALS) if percentages else None


def is_tree_project(project: Project) -> bool:
    return project.unit.strip().lower() == TREE_UNIT


def _local_date(moment: datetime) -> date:
    return moment.astimezone(ZoneInfo(get_settings().app_timezone)).date()


def _completion_of(snapshots: list[ProjectSnapshot], today: date) -> list[float]:
    return [
        capped_percent(s.progress.current_value, s.project.target_value)
        for s in snapshots
        if counts_toward_completion(s.project, today)
    ]


# ---------- needs attention ----------


def attention_reasons(snapshot: ProjectSnapshot, today: date) -> list[AttentionReason]:
    """Behind schedule, or active with no progress logged for STALE_AFTER_DAYS (counted from the start
    date when nothing was ever logged, so a project that started last week is not flagged)."""
    reasons: list[AttentionReason] = []
    if snapshot.progress.is_behind_schedule:
        reasons.append(AttentionReason.BEHIND_SCHEDULE)
    if snapshot.project.status == ProjectStatus.ACTIVE:
        last_activity = (
            _local_date(snapshot.progress.last_updated_at)
            if snapshot.progress.last_updated_at
            else snapshot.project.start_date
        )
        if (today - last_activity).days >= STALE_AFTER_DAYS:
            reasons.append(AttentionReason.NO_RECENT_UPDATE)
    return reasons


def build_attention(snapshots: list[ProjectSnapshot], today: date) -> list[AttentionItem]:
    items = []
    for snapshot in snapshots:
        reasons = attention_reasons(snapshot, today)
        if not reasons:
            continue
        last_updated = snapshot.progress.last_updated_at
        items.append(
            AttentionItem(
                id=snapshot.project.id,
                name=snapshot.project.name,
                type=snapshot.project.type,
                status=snapshot.project.status,
                owner_name=snapshot.project.owner.name,
                progress_percent=snapshot.progress.progress_percent,
                expected_percent=snapshot.progress.expected_percent,
                last_updated_at=last_updated,
                days_since_update=(today - _local_date(last_updated)).days if last_updated else None,
                reasons=reasons,
            )
        )
    # Furthest behind its timeline first.
    return sorted(items, key=lambda item: (item.progress_percent - item.expected_percent, item.id))


# ---------- summary ----------


def build_summary(snapshots: list[ProjectSnapshot], today: date) -> DashboardSummary:
    completion = _completion_of(snapshots, today)
    trees_planted = sum(s.progress.current_value for s in snapshots if is_tree_project(s.project))
    kg_per_tree = get_settings().co2_kg_per_tree_per_year
    return DashboardSummary(
        total_projects=len(snapshots),
        active_projects=sum(1 for s in snapshots if s.project.status == ProjectStatus.ACTIVE),
        average_completion_percent=average_completion(completion) or 0.0,
        completion_project_count=len(completion),
        trees_planted=trees_planted,
        estimated_co2_tonnes_per_year=round(trees_planted * kg_per_tree / KG_PER_TONNE, PERCENT_DECIMALS),
        co2_kg_per_tree_per_year=kg_per_tree,
        behind_schedule_count=sum(1 for s in snapshots if s.progress.is_behind_schedule),
        exceeded_target_count=sum(1 for s in snapshots if s.progress.is_target_exceeded),
        needs_attention_count=len(build_attention(snapshots, today)),
    )


# ---------- breakdowns ----------


def _type_label(project_type: ProjectType) -> str:
    return project_type.value.replace("_", " ").capitalize()


def build_by_type(snapshots: list[ProjectSnapshot], today: date) -> list[TypeBreakdown]:
    groups: dict[ProjectType, list[ProjectSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        groups[snapshot.project.type].append(snapshot)
    rows = [
        TypeBreakdown(
            type=project_type,
            label=_type_label(project_type),
            project_count=len(group),
            average_completion_percent=average_completion(_completion_of(group, today)),
        )
        for project_type, group in groups.items()
    ]
    return sorted(rows, key=lambda row: (-row.project_count, row.label))  # largest first


def build_by_state(snapshots: list[ProjectSnapshot], today: date) -> list[StateBreakdown]:
    groups: dict[str, list[ProjectSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        groups[snapshot.project.state].append(snapshot)
    rows = [
        StateBreakdown(
            state=state,
            project_count=len(group),
            average_completion_percent=average_completion(_completion_of(group, today)),
            trees_planted=sum(s.progress.current_value for s in group if is_tree_project(s.project)),
        )
        for state, group in groups.items()
    ]
    return sorted(rows, key=lambda row: (-row.project_count, row.state))


# ---------- trend ----------


def last_months(today: date, count: int = TREND_MONTHS) -> list[date]:
    """First day of each of the last `count` months, oldest first, ending with the current month."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return list(reversed(months))


def _month_end(first_day: date) -> date:
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _value_on(history: list[tuple[date, int]], day: date) -> int:
    """The running total as of `day`: the last update recorded on or before it (0 before any update).
    This is what "carry forward" means: a month with no update keeps the previous total."""
    value = 0
    for recorded_on, total in history:  # oldest first
        if recorded_on > day:
            break
        value = total
    return value


def build_trend(
    db: Session, snapshots: list[ProjectSnapshot], today: date, months: int = TREND_MONTHS
) -> list[TrendPoint]:
    """Average completion at the end of each of the last `months` months (the current month: as of today,
    so its point always equals the summary's figure)."""
    projects = [s.project for s in snapshots]
    histories: dict[int, list[tuple[date, int]]] = defaultdict(list)
    if projects:
        updates = db.execute(
            select(ProgressUpdate.project_id, ProgressUpdate.recorded_at, ProgressUpdate.value)
            .where(ProgressUpdate.project_id.in_([project.id for project in projects]))
            .order_by(ProgressUpdate.recorded_at, ProgressUpdate.id)
        )
        for project_id, recorded_at, value in updates:
            histories[project_id].append((_local_date(recorded_at), value))

    points = []
    for first_day in last_months(today, months):
        as_of = min(_month_end(first_day), today)
        completion = [
            capped_percent(_value_on(histories[project.id], as_of), project.target_value)
            for project in projects
            if counts_toward_completion(project, as_of)
        ]
        points.append(
            TrendPoint(
                month=first_day.strftime("%Y-%m"),
                average_completion_percent=average_completion(completion),
                project_count=len(completion),
            )
        )
    return points


# ---------- entry points used by the router ----------


def summary(db: Session, project_type: ProjectType | None) -> DashboardSummary:
    today = today_in_app_timezone()
    return build_summary(load_snapshots(db, project_type, today), today)


def by_type(db: Session, project_type: ProjectType | None) -> list[TypeBreakdown]:
    today = today_in_app_timezone()
    return build_by_type(load_snapshots(db, project_type, today), today)


def by_state(db: Session, project_type: ProjectType | None) -> list[StateBreakdown]:
    today = today_in_app_timezone()
    return build_by_state(load_snapshots(db, project_type, today), today)


def trend(db: Session, project_type: ProjectType | None) -> list[TrendPoint]:
    today = today_in_app_timezone()
    return build_trend(db, load_snapshots(db, project_type, today), today)


def attention(db: Session, project_type: ProjectType | None) -> list[AttentionItem]:
    today = today_in_app_timezone()
    return build_attention(load_snapshots(db, project_type, today), today)
