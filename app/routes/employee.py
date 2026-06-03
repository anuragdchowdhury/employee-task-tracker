"""Employee routes – dashboard and task submission."""

from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from app.utils.security import decode_session_token, SESSION_COOKIE
from app.utils.timezone import get_current_week, format_date
from app.services.auth_service import get_user_by_id
from app.services.submission_service import get_submission_for_week, submit_tasks

router = APIRouter(prefix="/employee")
templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request):
    """Extract and validate the current user from session cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = decode_session_token(token)
    if not data:
        return None
    user = get_user_by_id(data["user_id"])
    if not user or not user.get("active"):
        return None
    return user


@router.get("/dashboard")
async def employee_dashboard(request: Request):
    """Render the employee dashboard."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] == "admin":
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    week_start, week_end = get_current_week()
    submission = get_submission_for_week(user["_id"], week_start)

    # Format task dates for display
    formatted_tasks = []
    if submission:
        for task in submission.get("tasks", []):
            t = dict(task)
            cd = t.get("completion_date")
            if isinstance(cd, datetime):
                t["completion_date_fmt"] = format_date(cd)
            elif isinstance(cd, str):
                t["completion_date_fmt"] = cd
            else:
                t["completion_date_fmt"] = "N/A"
            formatted_tasks.append(t)

    return templates.TemplateResponse("employee/dashboard.html", {
        "request": request,
        "user": user,
        "week_start": format_date(week_start),
        "week_end": format_date(week_end),
        "submission": submission,
        "formatted_tasks": formatted_tasks,
        "success": request.query_params.get("success"),
    })


@router.post("/submit-tasks")
async def submit_weekly_tasks(request: Request):
    """Process the task submission form."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "employee":
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()

    # Parse dynamic task fields
    tasks = []
    idx = 0
    while True:
        task_name = form.get(f"task_name_{idx}")
        if task_name is None:
            break
        task_desc = form.get(f"task_description_{idx}", "")
        completion = form.get(f"completion_date_{idx}", "")

        completion_date = None
        if completion:
            try:
                completion_date = datetime.strptime(completion, "%Y-%m-%d")
            except ValueError:
                pass

        if task_name.strip():
            tasks.append({
                "task_name": task_name.strip(),
                "task_description": task_desc.strip(),
                "completion_date": completion_date,
            })
        idx += 1

    if not tasks:
        return RedirectResponse(url="/employee/dashboard?error=no_tasks", status_code=303)

    success = submit_tasks(user["_id"], user["name"], tasks)
    if success:
        return RedirectResponse(url="/employee/dashboard?success=1", status_code=303)
    else:
        return RedirectResponse(url="/employee/dashboard?error=already_submitted", status_code=303)
