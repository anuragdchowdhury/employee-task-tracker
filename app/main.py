"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

from app.database.mongodb import connect_db, close_db
from app.services.auth_service import create_default_admin
from app.routes import auth, employee, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    connect_db()
    create_default_admin()
    yield
    close_db()


app = FastAPI(
    title=os.getenv("APP_NAME", "Employee Weekly Task Tracker"),
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register route modules
app.include_router(auth.router)
app.include_router(employee.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Redirect root to login."""
    return RedirectResponse(url="/login", status_code=303)
