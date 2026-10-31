from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings


def tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_local() -> datetime:
    return datetime.now(tz())


def today() -> date:
    return now_local().date()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_bounds(day: date | None = None) -> tuple[date, date]:
    start = monday_of(day or today())
    return start, start + timedelta(days=6)


def next_or_current_week_start() -> date:
    """Sunday evening planning targets the week that starts the coming Monday.

    On Sunday, generate next week's menu. Other days, operate on the current week.
    """
    local = now_local()
    start, _ = week_bounds(local.date())
    if local.weekday() == 6:
        return start + timedelta(days=7)
    return start


def combine_local(d: date, hhmm: str) -> datetime:
    hour, minute = (int(part) for part in hhmm.split(":")[:2])
    return datetime.combine(d, time(hour=hour, minute=minute), tzinfo=tz())


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5
