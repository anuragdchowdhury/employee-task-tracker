"""MongoDB connection module."""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "employee_task_tracker")

client: MongoClient = None
db = None


def connect_db():
    """Establish MongoDB connection and return the database instance."""
    global client, db
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]

    # Create indexes
    db.employees.create_index("username", unique=True)
    db.employees.create_index("employee_code", unique=True)
    db.weekly_submissions.create_index([("employee_id", 1), ("week_start", 1)], unique=True)

    return db


def get_db():
    """Return the current database instance."""
    global db
    if db is None:
        connect_db()
    return db


def close_db():
    """Close the MongoDB connection."""
    global client
    if client:
        client.close()
