"""Employee model helpers."""

from datetime import datetime
from app.utils.timezone import now_ist


def create_employee_doc(
    employee_code: str,
    name: str,
    email: str,
    username: str,
    password_hash: str,
    role: str = "employee",
    team: str = "",
    active: bool = True,
) -> dict:
    """Return a dictionary ready to insert into the employees collection."""
    return {
        "employee_code": employee_code.strip().upper(),
        "name": name.strip(),
        "email": email.strip().lower(),
        "username": username.strip().lower(),
        "password_hash": password_hash,
        "role": role,
        "team": team.strip() if team else "",
        "active": active,
        "created_at": now_ist(),
    }
