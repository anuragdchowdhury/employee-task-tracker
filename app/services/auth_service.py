"""Authentication service – user lookup, creation, verification."""

from bson import ObjectId
from app.database.mongodb import get_db
from app.models.employee import create_employee_doc
from app.utils.security import hash_password, verify_password


def authenticate_user(username: str, password: str) -> dict | None:
    """Verify credentials and return the user doc, or None."""
    db = get_db()
    user = db.employees.find_one({"username": username.strip().lower()})
    if user and user.get("active") and verify_password(password, user["password_hash"]):
        return user
    return None


def get_user_by_id(user_id: str) -> dict | None:
    """Fetch a user by ObjectId string."""
    db = get_db()
    return db.employees.find_one({"_id": ObjectId(user_id)})


def create_default_admin():
    """Create the default admin account if none exists."""
    db = get_db()
    if db.employees.find_one({"role": "admin"}) is None:
        doc = create_employee_doc(
            employee_code="ADMIN001",
            name="Administrator",
            email="admin@company.com",
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            team="Management",
        )
        db.employees.insert_one(doc)
        print("✅ Default admin account created — username: admin / password: admin123")


def create_employee(employee_code, name, email, username, password, role="employee", team=""):
    """Create a new employee account."""
    db = get_db()
    doc = create_employee_doc(
        employee_code=employee_code,
        name=name,
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=role,
        team=team,
    )
    return db.employees.insert_one(doc)


def update_employee(employee_id: str, data: dict):
    """Update employee fields."""
    db = get_db()
    db.employees.update_one({"_id": ObjectId(employee_id)}, {"$set": data})


def toggle_employee_status(employee_id: str):
    """Toggle the active status of an employee."""
    db = get_db()
    emp = db.employees.find_one({"_id": ObjectId(employee_id)})
    if emp:
        db.employees.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": {"active": not emp["active"]}},
        )


def reset_employee_password(employee_id: str, new_password: str):
    """Reset an employee's password."""
    db = get_db()
    db.employees.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {"password_hash": hash_password(new_password)}},
    )


def get_all_employees():
    """Return all employees sorted by name."""
    db = get_db()
    return list(db.employees.find().sort("name", 1))


def get_employee_by_id(employee_id: str):
    """Return a single employee by ID."""
    db = get_db()
    return db.employees.find_one({"_id": ObjectId(employee_id)})


def get_all_teams():
    """Return a list of all unique teams."""
    db = get_db()
    teams = list(db.teams.find().sort("name", 1))
    return [t["name"] for t in teams if t.get("name")]
