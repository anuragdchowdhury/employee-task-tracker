"""Admin routes – dashboard, employee management, reports."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.utils.security import decode_session_token, SESSION_COOKIE
from app.utils.timezone import format_date, format_datetime
from app.database.mongodb import get_db
from app.services.auth_service import (
    get_user_by_id,
    get_all_employees,
    get_employee_by_id,
    create_employee,
    update_employee,
    toggle_employee_status,
    reset_employee_password,
    get_all_teams,
)
from app.services.submission_service import (
    get_weekly_dashboard_data,
    get_employee_history,
    get_submission_by_id,
    generate_whatsapp_report,
    revert_submission,
)
from app.services.report_service import (
    get_report_data,
    generate_csv,
    generate_excel,
    generate_pdf,
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def get_admin_user(request: Request):
    """Extract the current user and verify admin role."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    data = decode_session_token(token)
    if not data or data.get("role") != "admin":
        return None
    user = get_user_by_id(data["user_id"])
    if not user or user["role"] != "admin":
        return None
    return user


@router.get("/dashboard")
async def admin_dashboard(request: Request, team: str = "All"):
    """Render the admin dashboard with weekly stats."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dashboard = get_weekly_dashboard_data(team)
    teams = get_all_teams()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "dashboard": dashboard,
        "teams": teams,
        "selected_team": team,
    })


@router.get("/employees")
async def list_employees(request: Request, team: str = "All"):
    """Render the employee list view with optional team filter."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    query = {}
    if team != "All":
        query["team"] = team

    employees = list(db.employees.find(query).sort("name", 1))
    
    return templates.TemplateResponse("admin/employees.html", {
        "request": request,
        "user": user,
        "employees": employees,
        "teams": get_all_teams(),
        "selected_team": team,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.get("/employees/new")
async def new_employee_form(request: Request):
    """Render the new employee creation form."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("admin/employee_form.html", {
        "request": request,
        "user": user,
        "employee": None,
        "teams": get_all_teams(),
        "mode": "create",
        "error": None,
    })


@router.post("/employees/new")
async def create_new_employee(
    request: Request,
    employee_code: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("employee"),
    team: str = Form(""),
):
    """Process new employee creation."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        create_employee(employee_code, name, email, username, password, role, team)
        return RedirectResponse(url="/admin/employees?success=created", status_code=303)
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            error_msg = "Employee code or username already exists."
        return templates.TemplateResponse("admin/employee_form.html", {
            "request": request,
            "user": user,
            "employee": None,
            "teams": get_all_teams(),
            "mode": "create",
            "error": error_msg,
        })


@router.get("/employees/{employee_id}/edit")
async def edit_employee_form(request: Request, employee_id: str):
    """Render the employee edit form."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    emp = get_employee_by_id(employee_id)
    if not emp:
        return RedirectResponse(url="/admin/employees?error=not_found", status_code=303)

    return templates.TemplateResponse("admin/employee_form.html", {
        "request": request,
        "user": user,
        "employee": emp,
        "teams": get_all_teams(),
        "mode": "edit",
        "error": None,
    })


@router.post("/employees/{employee_id}/edit")
async def update_employee_details(
    request: Request,
    employee_id: str,
    employee_code: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form("employee"),
    team: str = Form(""),
):
    """Process employee update."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        update_employee(employee_id, {
            "employee_code": employee_code.strip().upper(),
            "name": name.strip(),
            "email": email.strip().lower(),
            "role": role,
            "team": team.strip(),
        })
        return RedirectResponse(url="/admin/employees?success=updated", status_code=303)
    except Exception as e:
        emp = get_employee_by_id(employee_id)
        return templates.TemplateResponse("admin/employee_form.html", {
            "request": request,
            "user": user,
            "employee": emp,
            "teams": get_all_teams(),
            "mode": "edit",
            "error": str(e),
        })


@router.post("/employees/{employee_id}/toggle")
async def toggle_status(request: Request, employee_id: str):
    """Toggle employee active status."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    toggle_employee_status(employee_id)
    return RedirectResponse(url="/admin/employees?success=toggled", status_code=303)


@router.post("/employees/{employee_id}/reset-password")
async def reset_password(
    request: Request,
    employee_id: str,
    new_password: str = Form(...),
):
    """Reset an employee's password."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    reset_employee_password(employee_id, new_password)
    return RedirectResponse(url="/admin/employees?success=password_reset", status_code=303)


@router.get("/employees/{employee_id}/history")
async def employee_history(request: Request, employee_id: str):
    """View submission history for an employee."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    emp = get_employee_by_id(employee_id)
    if not emp:
        return RedirectResponse(url="/admin/employees?error=not_found", status_code=303)

    history = get_employee_history(employee_id)

    return templates.TemplateResponse("admin/employee_history.html", {
        "request": request,
        "user": user,
        "employee": emp,
        "history": history,
    })


@router.get("/submissions/{submission_id}")
async def view_task_details(request: Request, submission_id: str):
    """View detailed tasks for a specific submission."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    sub = get_submission_by_id(submission_id)
    if not sub:
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    # Format task dates
    formatted_tasks = []
    for task in sub.get("tasks", []):
        t = dict(task)
        cd = t.get("completion_date")
        if cd:
            t["completion_date_fmt"] = format_date(cd)
        else:
            t["completion_date_fmt"] = "N/A"
        formatted_tasks.append(t)

    return templates.TemplateResponse("admin/task_details.html", {
        "request": request,
        "user": user,
        "submission": sub,
        "formatted_tasks": formatted_tasks,
        "week_start": format_date(sub["week_start"]),
        "week_end": format_date(sub["week_end"]),
        "submitted_at": format_datetime(sub["submitted_at"]),
    })


@router.post("/submissions/{submission_id}/revert")
async def revert_task_submission(request: Request, submission_id: str):
    """Revert an employee's submission for the current week."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    result = revert_submission(submission_id)
    if result == "success":
        return RedirectResponse(url="/admin/dashboard?success=reverted", status_code=303)
    elif result == "not_current_week":
        return RedirectResponse(url="/admin/dashboard?error=not_current_week", status_code=303)
    else:
        return RedirectResponse(url="/admin/dashboard?error=not_found", status_code=303)


@router.get("/whatsapp-report")
async def whatsapp_report(request: Request):
    """Return the WhatsApp report as JSON."""
    user = get_admin_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    report = generate_whatsapp_report()
    return JSONResponse({"report": report})


@router.get("/reports")
async def admin_reports(request: Request):
    """Render the reports page and optional data preview."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Date parsing
    start_str = request.query_params.get("start_date", "")
    end_str = request.query_params.get("end_date", "")
    team = request.query_params.get("team", "All")
    employee_id = request.query_params.get("employee_id", "All")

    start_date = None
    end_date = None
    if start_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_str:
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Defaults
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).date()
    if not end_date:
        end_date = datetime.now().date()

    # Load filters
    teams = get_all_teams()
    
    # Load employees for the dropdown (filter by team if selected)
    db = get_db()
    emp_query = {"role": "employee"}
    if team != "All":
        emp_query["team"] = team
    employees = list(db.employees.find(emp_query).sort("name", 1))

    report_data = None
    if start_str and end_str:
        # User requested a preview
        report_data = get_report_data(start_date, end_date, team, employee_id)

    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "user": user,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "teams": teams,
        "selected_team": team,
        "employees": employees,
        "selected_employee": employee_id,
        "report_data": report_data,
    })


@router.get("/reports/export")
async def export_report(
    request: Request,
    start_date: str,
    end_date: str,
    format: str,
    team: str = "All",
    employee_id: str = "All",
):
    """Export the report in the requested format."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return RedirectResponse(url="/admin/reports?error=invalid_dates", status_code=303)

    data = get_report_data(sd, ed, team, employee_id)
    filename_base = f"task_report_{start_date}_to_{end_date}"

    if format == "csv":
        buffer = generate_csv(data)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
        )
    elif format == "xlsx":
        buffer = generate_excel(data)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"}
        )
    elif format == "pdf":
        buffer = generate_pdf(data, title=f"Task Report ({start_date} to {end_date})")
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"}
        )
    
    return RedirectResponse(url="/admin/reports?error=invalid_format", status_code=303)


@router.get("/teams")
async def manage_teams(request: Request):
    """Render the team management page."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    teams = list(db.teams.find().sort("name", 1))

    return templates.TemplateResponse("admin/teams.html", {
        "request": request,
        "user": user,
        "teams": teams,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.post("/teams/create")
async def create_team(request: Request, name: str = Form(...)):
    """Create a new team."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    name = name.strip()
    if not name:
        return RedirectResponse(url="/admin/teams?error=invalid_name", status_code=303)

    if db.teams.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}):
        return RedirectResponse(url="/admin/teams?error=duplicate", status_code=303)

    db.teams.insert_one({"name": name})
    return RedirectResponse(url="/admin/teams?success=created", status_code=303)


@router.post("/teams/{team_id}/delete")
async def delete_team(request: Request, team_id: str):
    """Delete a team."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    from bson import ObjectId
    db = get_db()
    db.teams.delete_one({"_id": ObjectId(team_id)})
    return RedirectResponse(url="/admin/teams?success=deleted", status_code=303)

