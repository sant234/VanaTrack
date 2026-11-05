"""Fill the database with demo users, projects, progress history and matching activity (DATABASE.md 6).

Usage (run from the backend/ folder):
    python -m scripts.seed            -> changes nothing; explains how to use it
    python -m scripts.seed --reset    -> WIPES every user, project, progress update and activity entry
                                         in the DATABASE_URL database, then loads the demo data
    python -m scripts.seed --add      -> keeps everything and only ADDS what is missing: demo users whose
                                         email does not exist yet, and demo projects whose name does not
                                         exist yet (each with its progress history and activity)

Safety:
- Nothing is deleted without --reset, and the target (host, port, database name only, never the password)
  is printed before anything happens.
- The wipe and the reload run in ONE transaction: if anything fails, the old data stays as it was.
- Running it twice gives the same result: the tables are emptied and their id counters restarted.
- --add never updates or deletes a row. Existing users keep their name, password, role and status; a
  project whose name already exists is skipped with its whole history. Running it twice adds nothing
  the second time. --add and --reset cannot be combined.

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

from sqlalchemy import select, text
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
# Any fixed number works: --add holds this lock, so two runs at the same time cannot both add a project.
ADD_MODE_LOCK_KEY = 2026_1105
OWNER_ROLES = {UserRole.MANAGER, UserRole.ADMIN}


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


def _new_user(seed: SeedUser, password_hash: str, clock: Clock) -> User:
    return User(
        name=seed.name,
        email=seed.email,
        password_hash=password_hash,
        role=seed.role,
        created_at=clock.at(-USERS_CREATED_DAYS_AGO, PROJECT_CREATED_AT),
    )


def create_users(db: Session, seeds: list[SeedUser], clock: Clock) -> dict[str, User]:
    """Insert these demo users, all with the demo password."""
    password_hash = hash_password(DEMO_PASSWORD)  # one hash for all: bcrypt is slow on purpose
    users = {seed.key: _new_user(seed, password_hash, clock) for seed in seeds}
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
    users = create_users(db, USERS, clock)
    for seed in PROJECTS:
        create_project(db, seed, users[seed.owner_key], clock)
    db.commit()
    update_count = sum(len(project.updates) for project in PROJECTS)
    return (
        f"Seeded {len(USERS)} users, {len(PROJECTS)} projects and {update_count} progress updates. "
        f"Log in as any of: {', '.join(user.email for user in USERS)} (password in the README)."
    )


# ---------- --add: only add what is missing ----------


def _existing_demo_users(db: Session) -> dict[str, User]:
    """Demo users that already exist, matched by email (unique in the database)."""
    emails = [seed.email for seed in USERS]
    by_email = {user.email: user for user in db.scalars(select(User).where(User.email.in_(emails)))}
    return {seed.key: by_email[seed.email] for seed in USERS if seed.email in by_email}


def _check_existing_owners(existing: dict[str, User]) -> None:
    """An existing account is never changed, so one that cannot own projects stops the run instead."""
    for owner_key in sorted({project.owner_key for project in PROJECTS}):
        user = existing.get(owner_key)
        if user is not None and (user.role not in OWNER_ROLES or not user.is_active):
            state = "active" if user.is_active else "inactive"
            raise SeedDataError(
                f"{user.email} already exists as an {state} {user.role}, so it cannot own the demo projects. "
                "Make it an active manager first."
            )


def add_missing(db: Session, today: date) -> str:
    """Insert only the demo users and projects that do not exist yet. Never updates or deletes a row."""
    for project in PROJECTS:
        check_history(project)  # before touching anything
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADD_MODE_LOCK_KEY})
    clock = Clock(today, ZoneInfo(get_settings().app_timezone))

    existing_users = _existing_demo_users(db)
    _check_existing_owners(existing_users)
    new_user_seeds = [seed for seed in USERS if seed.key not in existing_users]
    users = existing_users | (create_users(db, new_user_seeds, clock) if new_user_seeds else {})

    names = [project.name for project in PROJECTS]
    existing_names = set(db.scalars(select(Project.name).where(Project.name.in_(names))))
    new_projects = [seed for seed in PROJECTS if seed.name not in existing_names]
    for seed in new_projects:
        create_project(db, seed, users[seed.owner_key], clock)
    db.commit()  # users, projects, progress and activity are saved together, or not at all
    return add_summary(new_user_seeds, new_projects, sorted(existing_names))


def add_summary(new_users: list[SeedUser], new_projects: list[SeedProject], skipped: list[str]) -> str:
    update_count = sum(len(project.updates) for project in new_projects)
    status_changes = sum(project.status_changed_days_ago is not None for project in new_projects)
    activity_count = len(new_projects) + update_count + status_changes
    created_users = ", ".join(seed.email for seed in new_users) or "none (all demo users already existed)"
    skipped_text = f": {', '.join(skipped)}." if skipped else "."
    return "\n".join(
        [
            f"Created users: {created_users}.",
            f"Created {len(new_projects)} projects, {update_count} progress updates "
            f"and {activity_count} activity entries.",
            f"Skipped {len(skipped)} projects that already existed{skipped_text}",
        ]
    )


# ---------- command line ----------


def describe_target(db: Session) -> str:
    """Host, port and database name only. Never the password or the full connection URL."""
    bind = db.get_bind()
    url: URL = getattr(bind, "engine", bind).url
    return f"database '{url.database}' on {url.host or 'localhost'}:{url.port or 5432}"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load VanaTrack demo data.", allow_abbrev=False)
    # "Wipe everything" and "keep everything" cannot both be meant, so argparse refuses both (exit code 2).
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--reset",
        action="store_true",
        help="Delete ALL users, projects, progress and activity in DATABASE_URL, then load the demo data.",
    )
    mode.add_argument(
        "--add",
        action="store_true",
        help="Keep all existing data; only add demo users and demo projects that do not exist yet.",
    )
    return parser.parse_args(argv)


def explain_usage(target: str) -> None:
    print(f"Nothing was changed in {target}.")
    print("  python -m scripts.seed --add     keeps all data; adds only missing demo users and projects")
    print(
        "  python -m scripts.seed --reset   deletes ALL users, projects, progress and activity, then reloads"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with SessionLocal() as db:
        target = describe_target(db)
        if not (args.reset or args.add):
            explain_usage(target)
            return 0
        today = today_in_app_timezone()
        print(f"{'Resetting' if args.reset else 'Adding missing demo data to'} {target} ...")
        try:
            print(reset_and_seed(db, today) if args.reset else add_missing(db, today))
        except SeedDataError as error:
            db.rollback()
            print(f"Error: {error} Nothing was changed.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
