"""Submission service – create, query, and report on weekly submissions."""

from datetime import datetime
from bson import ObjectId
from app.database.mongodb import get_db
from app.models.submission import create_submission_doc
from app.utils.timezone import get_current_week, format_date, format_datetime


def get_submission_for_week(employee_id: ObjectId, week_start) -> dict | None:
    """Return the submission for a given employee and week, or None."""
    db = get_db()
    return db.weekly_submissions.find_one({
        "employee_id": employee_id,
        "week_start": datetime.combine(week_start, datetime.min.time()),
    })


def submit_tasks(employee_id: ObjectId, employee_name: str, tasks: list[dict]) -> bool:
    """
    Submit weekly tasks for the current week.
    Returns True on success, False if already submitted.
    """
    week_start, week_end = get_current_week()

    # Check if already submitted
    if get_submission_for_week(employee_id, week_start):
        return False

    doc = create_submission_doc(
        employee_id=employee_id,
        employee_name=employee_name,
        week_start=week_start,
        week_end=week_end,
        tasks=tasks,
    )
    db = get_db()
    db.weekly_submissions.insert_one(doc)
    return True


def get_weekly_dashboard_data():
    """Return dashboard statistics and employee submission statuses."""
    db = get_db()
    week_start, week_end = get_current_week()
    ws_dt = datetime.combine(week_start, datetime.min.time())

    employees = list(db.employees.find({"role": "employee"}).sort("name", 1))
    submissions = list(db.weekly_submissions.find({"week_start": ws_dt}))

    submitted_ids = {str(s["employee_id"]) for s in submissions}
    submission_map = {str(s["employee_id"]): s for s in submissions}

    total = len(employees)
    updated = len(submitted_ids & {str(e["_id"]) for e in employees})
    pending = total - updated

    employee_statuses = []
    for emp in employees:
        eid = str(emp["_id"])
        sub = submission_map.get(eid)
        employee_statuses.append({
            "employee": emp,
            "submitted": eid in submitted_ids,
            "submission_date": format_datetime(sub["submitted_at"]) if sub else None,
            "submission_id": str(sub["_id"]) if sub else None,
        })

    return {
        "total": total,
        "updated": updated,
        "pending": pending,
        "week_start": format_date(week_start),
        "week_end": format_date(week_end),
        "employee_statuses": employee_statuses,
    }


def get_employee_history(employee_id: str):
    """Return all submissions for an employee, newest first."""
    db = get_db()
    subs = list(
        db.weekly_submissions.find({"employee_id": ObjectId(employee_id)})
        .sort("week_start", -1)
    )
    result = []
    for s in subs:
        result.append({
            "id": str(s["_id"]),
            "week_start": format_date(s["week_start"]),
            "week_end": format_date(s["week_end"]),
            "submitted_at": format_datetime(s["submitted_at"]),
            "task_count": len(s.get("tasks", [])),
        })
    return result


def get_submission_by_id(submission_id: str):
    """Return a single submission by its ID."""
    db = get_db()
    return db.weekly_submissions.find_one({"_id": ObjectId(submission_id)})


def generate_whatsapp_report():
    """Generate the WhatsApp summary report for the current week."""
    db = get_db()
    week_start, week_end = get_current_week()
    ws_dt = datetime.combine(week_start, datetime.min.time())

    submissions = list(
        db.weekly_submissions.find({"week_start": ws_dt}).sort("employee_name", 1)
    )

    lines = [
        f"📋 *Weekly Task Update*",
        f"📅 {format_date(week_start)} – {format_date(week_end)}",
        "",
    ]

    if not submissions:
        lines.append("No submissions yet for this week.")
        return "\n".join(lines)

    for sub in submissions:
        lines.append("---")
        lines.append(f"👤 *{sub['employee_name']}*")
        lines.append("")
        for idx, task in enumerate(sub.get("tasks", []), 1):
            lines.append(f"{idx}. *{task['task_name']}*")
            lines.append(f"   📝 Description: {task.get('task_description', 'N/A')}")
            completion = task.get("completion_date")
            if isinstance(completion, datetime):
                completion = format_date(completion)
            elif isinstance(completion, str):
                # Try parsing if string
                try:
                    completion = format_date(datetime.strptime(completion, "%Y-%m-%d"))
                except Exception:
                    pass
            lines.append(f"   ✅ Completion: {completion or 'N/A'}")
            lines.append("")

    lines.append("---")
    return "\n".join(lines)
