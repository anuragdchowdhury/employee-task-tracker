"""Weekly submission model helpers."""

from datetime import date, datetime
from app.utils.timezone import now_ist
from bson import ObjectId


def create_submission_doc(
    employee_id: ObjectId,
    employee_name: str,
    week_start: date,
    week_end: date,
    tasks: list[dict],
) -> dict:
    """Return a dictionary ready to insert into the weekly_submissions collection."""
    return {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "week_start": datetime.combine(week_start, datetime.min.time()),
        "week_end": datetime.combine(week_end, datetime.min.time()),
        "submitted_at": now_ist(),
        "tasks": tasks,
    }
