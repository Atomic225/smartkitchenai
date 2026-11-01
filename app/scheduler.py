from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.services.jobs import job_chef_calls, job_generate_weekly_menu, job_grocery_reminders

_scheduler: BackgroundScheduler | None = None


def _run(job_fn) -> None:
    db = SessionLocal()
    try:
        job_fn(db)
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    timezone = get_settings().timezone
    scheduler = BackgroundScheduler(timezone=timezone, job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600})
    scheduler.add_job(
        lambda: _run(job_generate_weekly_menu),
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=timezone),
        id="weekly_menu_sunday",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run(job_grocery_reminders),
        CronTrigger(minute=10, timezone=timezone),
        id="grocery_reminders_hourly",
        replace_existing=True,
    )
    # Check chef calls every minute so user-configured exact times fire promptly
    scheduler.add_job(
        lambda: _run(job_chef_calls),
        CronTrigger(minute="*", timezone=timezone),
        id="chef_calls",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    db = SessionLocal()
    try:
        job_generate_weekly_menu(db)
        job_grocery_reminders(db)
        job_chef_calls(db)
    finally:
        db.close()
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
