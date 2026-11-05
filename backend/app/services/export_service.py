"""CSV export of the project list.

The rows come from project_service.list_projects, the same query as the project list and the dashboard,
so the file always shows the same numbers as the screen.

CSV injection: a spreadsheet treats a cell that starts with =, +, -, @, tab or carriage return as a formula.
Any such text cell (e.g. a project named "=HYPERLINK(...)") is prefixed with ' so it is shown as text.
"""

import csv
import io
from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.schemas.project import ProjectOut

FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
FORMULA_ESCAPE = "'"
# Excel only reads a CSV as UTF-8 (₹, →, Indian names) when the file starts with this byte-order mark.
UTF8_BOM = "\ufeff"


def neutralize_formula(value: object) -> object:
    """Prefix text that a spreadsheet would run as a formula. Numbers are left as they are."""
    if isinstance(value, str) and value.startswith(FORMULA_TRIGGERS):
        return FORMULA_ESCAPE + value
    return value


def _yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def _local_timestamp(moment: datetime | None) -> str:
    """e.g. 2026-10-16 10:00, in the app's timezone (the same one the dashboard uses)."""
    if moment is None:
        return ""
    return moment.astimezone(ZoneInfo(get_settings().app_timezone)).strftime("%Y-%m-%d %H:%M")


# (header, how to read the value from a project), in column order.
COLUMNS: list[tuple[str, Callable[[ProjectOut], object]]] = [
    ("ID", lambda p: p.id),
    ("Name", lambda p: p.name),
    ("Type", lambda p: p.type.value),
    ("Status", lambda p: p.status.value),
    ("State", lambda p: p.state),
    ("District", lambda p: p.district or ""),
    ("Owner", lambda p: p.owner.name),
    ("Unit", lambda p: p.unit),
    ("Target", lambda p: p.target_value),
    ("Current", lambda p: p.current_value),
    ("Progress %", lambda p: p.progress_percent),
    ("Expected %", lambda p: p.expected_percent),
    ("Behind schedule", lambda p: _yes_no(p.is_behind_schedule)),
    ("Exceeded target", lambda p: _yes_no(p.is_target_exceeded)),
    ("Start date", lambda p: p.start_date.isoformat()),
    ("End date", lambda p: p.end_date.isoformat()),
    ("Budget (INR)", lambda p: "" if p.budget_inr is None else f"{p.budget_inr:.2f}"),
    ("Last update", lambda p: _local_timestamp(p.last_updated_at)),
]


def build_projects_csv(projects: list[ProjectOut]) -> str:
    """The whole file as text: a header row, then one row per project in the given order."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")  # RFC 4180 line endings
    writer.writerow([header for header, _read in COLUMNS])
    for project in projects:
        writer.writerow([neutralize_formula(read(project)) for _header, read in COLUMNS])
    return UTF8_BOM + buffer.getvalue()


def export_filename(today: date) -> str:
    return f"vanatrack-projects-{today.isoformat()}.csv"
