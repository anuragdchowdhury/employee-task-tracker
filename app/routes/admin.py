"""Admin routes – dashboard, employee management, reports."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.utils.security import decode_session_token, SESSION_COOKIE
from app.utils.timezone import format_date, format_datetime
from app.services.auth_service import (
    get_user_by_id,
    get_all_employees,
    get_employee_by_id,
    create_employee,
    update_employee,
    toggle_employee_status,
    reset_employee_password,
)
from app.services.submission_service import (
    get_weekly_dashboard_data,
    get_employee_history,
    get_submission_by_id,
    generate_whatsapp_report,
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
async def admin_dashboard(request: Request):
    """Render the admin dashboard with weekly stats."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    dashboard = get_weekly_dashboard_data()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "dashboard": dashboard,
    })


@router.get("/employees")
async def employees_page(request: Request):
    """Render the employee management page."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    employees = get_all_employees()
    return templates.TemplateResponse("admin/employees.html", {
        "request": request,
        "user": user,
        "employees": employees,
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
):
    """Process new employee creation."""
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        create_employee(employee_code, name, email, username, password, role)
        return RedirectResponse(url="/admin/employees?success=created", status_code=303)
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            error_msg = "Employee code or username already exists."
        return templates.TemplateResponse("admin/employee_form.html", {
            "request": request,
            "user": user,
            "employee": None,
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
        })
        return RedirectResponse(url="/admin/employees?success=updated", status_code=303)
    except Exception as e:
        emp = get_employee_by_id(employee_id)
        return templates.TemplateResponse("admin/employee_form.html", {
            "request": request,
            "user": user,
            "employee": emp,
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


@router.get("/whatsapp-report")
async def whatsapp_report(request: Request):
    """Return the WhatsApp report as JSON."""
    user = get_admin_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    report = generate_whatsapp_report()
    return JSONResponse({"report": report})
