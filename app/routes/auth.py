"""Authentication routes – login / logout."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth_service import authenticate_user
from app.utils.security import create_session_token, SESSION_COOKIE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
async def login_page(request: Request):
    """Render the login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form submission."""
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password, or account is disabled.",
        })

    token = create_session_token(str(user["_id"]), user["role"])

    if user["role"] == "admin":
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
    else:
        response = RedirectResponse(url="/employee/dashboard", status_code=303)

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Clear session and redirect to login."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
