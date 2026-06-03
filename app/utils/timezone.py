"""Timezone utilities for IST (Asia/Kolkata)."""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Return the current datetime in IST."""
    return datetime.now(IST)


def get_current_week() -> tuple:
    """
    Return (week_start, week_end) for the current week.
    Week starts Monday 00:00 IST and ends Sunday 23:59 IST.
    """
    today = now_ist().date()
    # Monday is 0, Sunday is 6
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def format_date(d) -> str:
    """Format a date as DD-MM-YYYY."""
    if d is None:
        return ""
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d-%m-%Y")


def format_datetime(dt) -> str:
    """Format a datetime as DD-MM-YYYY HH:MM."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST).strftime("%d-%m-%Y %H:%M")
