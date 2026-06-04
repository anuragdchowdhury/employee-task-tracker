"""Submission service – create, query, and report on weekly submissions."""

from datetime import datetime, timedelta
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


def get_weekly_dashboard_data(team=None):
    """Return dashboard statistics and employee submission statuses."""
    db = get_db()
    week_start, week_end = get_current_week()
    ws_dt = datetime.combine(week_start, datetime.min.time())

    query = {"role": "employee"}
    if team and team != "All":
        query["team"] = team

    employees = list(db.employees.find(query).sort("name", 1))
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
        "team_filter": team,
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


def get_employee_history_by_date_range(employee_id: str, start_date=None, end_date=None):
    """
    Return submissions for an employee within a date range, grouped by week.
    Defaults to the last 30 days if no range is given.
    Returns a list of week groups, each containing formatted submission data and tasks.
    """
    db = get_db()

    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).date()
    if not end_date:
        end_date = datetime.now().date()

    query = {
        "employee_id": ObjectId(employee_id),
        "week_start": {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date, datetime.min.time()),
        },
    }

    subs = list(db.weekly_submissions.find(query).sort("week_start", -1))

    week_groups = []
    for s in subs:
        tasks = []
        for task in s.get("tasks", []):
            t = dict(task)
            cd = t.get("completion_date")
            if isinstance(cd, datetime):
                t["completion_date_fmt"] = format_date(cd)
            elif isinstance(cd, str):
                t["completion_date_fmt"] = cd
            else:
                t["completion_date_fmt"] = "N/A"

            sd = t.get("start_date")
            if isinstance(sd, datetime):
                t["start_date_fmt"] = format_date(sd)
            elif isinstance(sd, str):
                t["start_date_fmt"] = sd
            else:
                t["start_date_fmt"] = "N/A"

            t.setdefault("task_type", "")
            tasks.append(t)

        week_groups.append({
            "id": str(s["_id"]),
            "week_start": format_date(s["week_start"]),
            "week_end": format_date(s["week_end"]),
            "submitted_at": format_datetime(s["submitted_at"]),
            "task_count": len(tasks),
            "tasks": tasks,
        })

    return week_groups


def get_submission_by_id(submission_id: str):
    """Return a single submission by its ID."""
    db = get_db()
    return db.weekly_submissions.find_one({"_id": ObjectId(submission_id)})


def revert_submission(submission_id: str) -> str:
    """
    Revert (delete) a submission, but only if it belongs to the current week.
    Returns 'success', 'not_found', or 'not_current_week'.
    """
    db = get_db()
    sub = db.weekly_submissions.find_one({"_id": ObjectId(submission_id)})
    if not sub:
        return "not_found"

    week_start, _ = get_current_week()
    ws_dt = datetime.combine(week_start, datetime.min.time())

    if sub["week_start"] != ws_dt:
        return "not_current_week"

    db.weekly_submissions.delete_one({"_id": ObjectId(submission_id)})
    return "success"


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
            task_type = task.get("task_type", "")
            type_label = f" [{task_type}]" if task_type else ""
            lines.append(f"{idx}. *{task['task_name']}*{type_label}")
            lines.append(f"   📝 Description: {task.get('task_description', 'N/A')}")
            start = task.get("start_date")
            if isinstance(start, datetime):
                start = format_date(start)
            elif isinstance(start, str):
                try:
                    start = format_date(datetime.strptime(start, "%Y-%m-%d"))
                except Exception:
                    pass
            lines.append(f"   🚀 Start: {start or 'N/A'}")
            completion = task.get("completion_date")
            if isinstance(completion, datetime):
                completion = format_date(completion)
            elif isinstance(completion, str):
                try:
                    completion = format_date(datetime.strptime(completion, "%Y-%m-%d"))
                except Exception:
                    pass
            lines.append(f"   ✅ Completion: {completion or 'N/A'}")
            lines.append("")

    lines.append("---")
    return "\n".join(lines)
