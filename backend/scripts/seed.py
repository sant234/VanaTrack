"""Fill the database with demo users, projects, progress history and matching activity (DATABASE.md 6).

Usage (run from the backend/ folder):
    python -m scripts.seed            -> changes nothing; explains how to use it
    python -m scripts.seed --reset    -> WIPES every user, project, progress update and activity entry
                                         in the DATABASE_URL database, then loads the demo data

Safety:
- Nothing is deleted without --reset, and the target (host, port, database name only, never the password)
  is printed before anything happens.
- The wipe and the reload run in ONE transaction: if anything fails, the old data stays as it was.
- Running it twice gives the same result: the tables are emptied and their id counters restarted.

All dates are relative to "today" in APP_TIMEZONE, so "behind schedule" and "no update in 30+ days" stay
true whenever the demo is reseeded. The history obeys the same rules as the API (see check_history).
One documented exception to "3-8 updates per project": the planned project starts in the future, so it
cannot have any valid update yet.
"""

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.activity_log import ActivityAction, ActivityEntityType
from app.models.progress_update import CORRECTION_NOTE_MIN_LENGTH, ProgressUpdate
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.activity_service import record_activity
from app.services.progress_service import UNREALISTIC_TARGET_MULTIPLIER, today_in_app_timezone

DEMO_PASSWORD = "Demo@1234"  # documented in DATABASE.md 6 and the README; demo accounts only

# Times of day (local) for seeded events, so the order within one day is always the same.
PROJECT_CREATED_AT = time(9, 0)
PROGRESS_RECORDED_AT = time(10, 0)
STATUS_CHANGED_AT = time(17, 0)
USERS_CREATED_DAYS_AGO = 400
PROJECT_CREATED_DAYS_BEFORE_START = 7
FUTURE_PROJECT_CREATED_DAYS_AGO = 3
CLOSED_STATUSES = {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED, ProjectStatus.ON_HOLD}

TABLES_TO_RESET = "activity_logs, progress_updates, projects, users"


class SeedDataError(Exception):
    """The demo data itself breaks a rule the API enforces. Fix the data below, not the rule."""


@dataclass(frozen=True)
class SeedUser:
    key: str
    name: str
    email: str
    role: UserRole


@dataclass(frozen=True)
class SeedUpdate:
    days_ago: int
    value: int
    correction_note: str | None = None


@dataclass(frozen=True)
class SeedProject:
    name: str
    type: ProjectType
    unit: str
    target_value: int
    state: str
    district: str
    owner_key: str
    status: ProjectStatus
    start_offset_days: int  # relative to today: negative = in the past
    end_offset_days: int
    description: str
    updates: list[SeedUpdate] = field(default_factory=list)
    # For completed / cancelled / on-hold projects: when the status changed from active.
    status_changed_days_ago: int | None = None


USERS = [
    SeedUser("admin", "Asha Rao", "admin@vanatrack.demo", UserRole.ADMIN),
    SeedUser("manager", "Ravi Kumar", "manager@vanatrack.demo", UserRole.MANAGER),
    SeedUser("manager2", "Meera Iyer", "manager2@vanatrack.demo", UserRole.MANAGER),
    SeedUser("viewer", "Vikram Shah", "viewer@vanatrack.demo", UserRole.VIEWER),
]

PROJECTS = [
    SeedProject(
        "Western Ghats Reforestation", ProjectType.AFFORESTATION, "trees", 1000, "Karnataka", "Shivamogga",
        "manager", ProjectStatus.ACTIVE, -300, 240,
        "The brief's project: 1,000 native saplings, now at 600. Log 850 live in the demo.",
        [SeedUpdate(270, 150), SeedUpdate(200, 320), SeedUpdate(120, 450), SeedUpdate(20, 600)],
    ),
    SeedProject(
        "Thar Solar Microgrid", ProjectType.SOLAR, "kW", 500, "Rajasthan", "Jodhpur",
        "manager2", ProjectStatus.ACTIVE, -330, 35,
        "Village microgrid. Panel deliveries slipped, so it is behind schedule.",
        [SeedUpdate(300, 50), SeedUpdate(220, 120), SeedUpdate(140, 180), SeedUpdate(25, 250)],
    ),
    SeedProject(
        "Chennai Coastal Mangroves", ProjectType.AFFORESTATION, "trees", 5000, "Tamil Nadu", "Chennai",
        "manager", ProjectStatus.ACTIVE, -360, 185,
        "Mangrove belt along the coast. Volunteers pushed it past its target.",
        [SeedUpdate(330, 1200), SeedUpdate(250, 2500), SeedUpdate(170, 3600), SeedUpdate(90, 4800),
         SeedUpdate(10, 5400)],
    ),
    SeedProject(
        "Pune Rainwater Harvesting", ProjectType.WATER_CONSERVATION, "kL water", 2000, "Maharashtra", "Pune",
        "manager2", ProjectStatus.ACTIVE, -270, 460,
        "Rooftop harvesting in housing societies. No report for over a month.",
        [SeedUpdate(240, 300), SeedUpdate(160, 650), SeedUpdate(45, 900)],
    ),
    SeedProject(
        "Nashik Waste Segregation", ProjectType.WASTE_MANAGEMENT, "kg waste", 10000, "Maharashtra", "Nashik",
        "manager", ProjectStatus.ACTIVE, -240, 125,
        "Ward-level segregation drive. Includes one corrected weighbridge reading.",
        [SeedUpdate(210, 2000), SeedUpdate(150, 4800),
         SeedUpdate(120, 4500, "Weighbridge recalibrated; earlier reading was 300 kg too high."),
         SeedUpdate(60, 6000), SeedUpdate(12, 7100)],
    ),
    SeedProject(
        "Dehradun School Rooftop Solar", ProjectType.SOLAR, "kW", 120, "Uttarakhand", "Dehradun",
        "manager2", ProjectStatus.COMPLETED, -365, -35,
        "Rooftop panels on twelve government schools. Finished on time.",
        [SeedUpdate(340, 30), SeedUpdate(250, 75), SeedUpdate(150, 110), SeedUpdate(60, 120)],
        status_changed_days_ago=35,
    ),
    SeedProject(
        "Jaisalmer Check Dams", ProjectType.WATER_CONSERVATION, "kL water", 800, "Rajasthan", "Jaisalmer",
        "manager", ProjectStatus.CANCELLED, -300, 65,
        "Check dams on seasonal streams. Cancelled when the land permit was withdrawn.",
        [SeedUpdate(260, 100), SeedUpdate(190, 180), SeedUpdate(130, 220), SeedUpdate(90, 260)],
        status_changed_days_ago=75,
    ),
    SeedProject(
        "Nilgiris Shola Restoration", ProjectType.AFFORESTATION, "trees", 3000, "Tamil Nadu", "Nilgiris",
        "manager2", ProjectStatus.ON_HOLD, -200, 350,
        "Shola grassland restoration, paused for the monsoon.",
        [SeedUpdate(180, 400), SeedUpdate(110, 900), SeedUpdate(70, 1100)],
        status_changed_days_ago=50,
    ),
    SeedProject(
        "Rishikesh River Clean-up", ProjectType.WASTE_MANAGEMENT, "kg waste", 5000, "Uttarakhand", "Dehradun",
        "manager", ProjectStatus.PLANNED, 30, 395,
        "Ghat clean-up starting next month, so no progress can be logged yet.",
    ),
    SeedProject(
        "Mysuru Urban Tree Canopy", ProjectType.AFFORESTATION, "trees", 2500, "Karnataka", "Mysuru",
        "manager2", ProjectStatus.ACTIVE, -180, 185,
        "Street trees along the ring road.",
        [SeedUpdate(160, 300), SeedUpdate(100, 700), SeedUpdate(50, 1100), SeedUpdate(8, 1350)],
    ),
]  # fmt: skip


# ---------- dates ----------


@dataclass(frozen=True)
class Clock:
    """Turns "N days ago at HH:MM" into an aware datetime in the app's timezone."""

    today: date
    zone: ZoneInfo

    def day(self, offset_days: int) -> date:
        return self.today + timedelta(days=offset_days)

    def at(self, offset_days: int, time_of_day: time) -> datetime:
        return datetime.combine(self.day(offset_days), time_of_day, tzinfo=self.zone)


def project_created_offset(project: SeedProject) -> int:
    """A week before the start, but never in the future (a planned project was created recently)."""
    return min(
        project.start_offset_days - PROJECT_CREATED_DAYS_BEFORE_START, -FUTURE_PROJECT_CREATED_DAYS_AGO
    )


# ---------- rules (the same ones the API enforces) ----------


def check_history(project: SeedProject) -> None:
    """Fail loudly if the demo data breaks a rule the API would refuse (ARCHITECTURE.md 7.2)."""
    previous_value, previous_days_ago = 0, None
    for update in project.updates:
        problem = None
        if -update.days_ago < project.start_offset_days or update.days_ago < 0:
            problem = "is before the start date or in the future"
        elif previous_days_ago is not None and update.days_ago >= previous_days_ago:
            problem = "is not later than the update before it"
        elif update.value > project.target_value * UNREALISTIC_TARGET_MULTIPLIER:
            problem = "is more than 10x the target"
        elif update.value <= previous_value and not _is_valid_correction(update, previous_value):
            problem = "does not go up and is not a correction with a note"
        elif (
            project.status_changed_days_ago is not None and update.days_ago <= project.status_changed_days_ago
        ):
            problem = "is not before the project was closed"
        if problem:
            raise SeedDataError(
                f"{project.name}: update {update.value} ({update.days_ago} days ago) {problem}."
            )
        previous_value, previous_days_ago = update.value, update.days_ago
    if (project.status in CLOSED_STATUSES) != (project.status_changed_days_ago is not None):
        raise SeedDataError(f"{project.name}: a closed or paused project needs a status-change date.")


def _is_valid_correction(update: SeedUpdate, previous_value: int) -> bool:
    note = (update.correction_note or "").strip()
    return update.value < previous_value and len(note) >= CORRECTION_NOTE_MIN_LENGTH


# ---------- loading ----------


def _log(
    db: Session,
    user: User,
    action: ActivityAction,
    entity_type: ActivityEntityType,
    entity_id: int,
    project_id: int,
    details: dict,
    when: datetime,
) -> None:
    """An activity entry dated when the change happened, not when the seed ran."""
    entry = record_activity(db, user, action, entity_type, entity_id, project_id, details)
    entry.created_at = when


def create_users(db: Session, clock: Clock) -> dict[str, User]:
    joined = clock.at(-USERS_CREATED_DAYS_AGO, PROJECT_CREATED_AT)
    password_hash = hash_password(DEMO_PASSWORD)  # one hash for all: bcrypt is slow on purpose
    users = {
        seed.key: User(
            name=seed.name, email=seed.email, password_hash=password_hash, role=seed.role, created_at=joined
        )
        for seed in USERS
    }
    db.add_all(users.values())
    db.flush()
    return users


def _log_project_event(
    db: Session, owner: User, project: Project, action: ActivityAction, details: dict, when: datetime
) -> None:
    _log(db, owner, action, ActivityEntityType.PROJECT, project.id, project.id, details, when)


def create_project(db: Session, seed: SeedProject, owner: User, clock: Clock) -> Project:
    """The project, its "created" entry, its progress history, and (if closed) its status change."""
    created_at = clock.at(project_created_offset(seed), PROJECT_CREATED_AT)
    status_changed_at = None
    if seed.status_changed_days_ago is not None:
        status_changed_at = clock.at(-seed.status_changed_days_ago, STATUS_CHANGED_AT)
    project = Project(
        name=seed.name,
        description=seed.description,
        type=seed.type,
        status=seed.status,
        target_value=seed.target_value,
        unit=seed.unit,
        state=seed.state,
        district=seed.district,
        start_date=clock.day(seed.start_offset_days),
        end_date=clock.day(seed.end_offset_days),
        owner_id=owner.id,
        created_at=created_at,
        updated_at=status_changed_at or created_at,
    )
    db.add(project)
    db.flush()  # assigns project.id
    _log_project_event(db, owner, project, ActivityAction.CREATED, {"name": project.name}, created_at)
    create_progress_history(db, seed, project, owner, clock)
    if status_changed_at:
        # Same shape the API writes when a project's status is edited (ARCHITECTURE.md 7.5).
        changes = {"status": {"from": ProjectStatus.ACTIVE.value, "to": seed.status.value}}
        details = {"name": project.name, "changes": changes}
        _log_project_event(db, owner, project, ActivityAction.UPDATED, details, status_changed_at)
    return project


def create_progress_history(
    db: Session, seed: SeedProject, project: Project, owner: User, clock: Clock
) -> None:
    previous_value = 0
    for update in seed.updates:
        recorded_at = clock.at(-update.days_ago, PROGRESS_RECORDED_AT)
        is_correction = update.correction_note is not None
        row = ProgressUpdate(
            project_id=project.id,
            value=update.value,
            previous_value=previous_value,
            is_correction=is_correction,
            note=update.correction_note,
            recorded_at=recorded_at,
            created_by=owner.id,
            created_at=recorded_at,
        )
        db.add(row)
        db.flush()
        details = {"from": previous_value, "to": update.value, "is_correction": is_correction}
        _log(
            db,
            owner,
            ActivityAction.PROGRESS_LOGGED,
            ActivityEntityType.PROGRESS_UPDATE,
            row.id,
            project.id,
            details,
            recorded_at,
        )
        previous_value = update.value


def reset_and_seed(db: Session, today: date) -> str:
    """Wipe the four tables and load the demo data, in one transaction. Returns a summary to print."""
    for project in PROJECTS:
        check_history(project)  # before touching anything
    clock = Clock(today, ZoneInfo(get_settings().app_timezone))
    db.execute(text(f"TRUNCATE {TABLES_TO_RESET} RESTART IDENTITY"))
    users = create_users(db, clock)
    for seed in PROJECTS:
        create_project(db, seed, users[seed.owner_key], clock)
    db.commit()
    update_count = sum(len(project.updates) for project in PROJECTS)
    return (
        f"Seeded {len(USERS)} users, {len(PROJECTS)} projects and {update_count} progress updates. "
        f"Log in as any of: {', '.join(user.email for user in USERS)} (password in the README)."
    )


# ---------- command line ----------


def describe_target(db: Session) -> str:
    """Host, port and database name only. Never the password or the full connection URL."""
    bind = db.get_bind()
    url: URL = getattr(bind, "engine", bind).url
    return f"database '{url.database}' on {url.host or 'localhost'}:{url.port or 5432}"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load VanaTrack demo data.", allow_abbrev=False)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete ALL users, projects, progress and activity in DATABASE_URL, then load the demo data.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with SessionLocal() as db:
        target = describe_target(db)
        if not args.reset:
            print(f"Nothing was changed in {target}.")
            print("This script deletes ALL users, projects, progress and activity, then loads demo data.")
            print("To do that, run:  python -m scripts.seed --reset")
            return 0
        print(f"Resetting {target} ...")
        try:
            print(reset_and_seed(db, today_in_app_timezone()))
        except SeedDataError as error:
            print(f"Error: {error} Nothing was changed.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
