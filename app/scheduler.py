from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.models import Member
from app.services.jobs import job_chef_calls, job_generate_weekly_menu, job_grocery_reminders
from app.services.whatsapp import send_text
from app.services.flat_chat import (
    get_or_create_evening_session,
    format_kickoff_message,
    format_hourly_reminder,
    FlatDecisionSession,
)
from app.services.timeutil import today, now_local

_scheduler: BackgroundScheduler | None = None


def _run(job_fn) -> None:
    db = SessionLocal()
    try:
        job_fn(db)
    finally:
        db.close()


def job_flat_evening_kickoff(db) -> str:
    """Triggered every evening at 6:00 PM: posts the 4 options for tomorrow."""
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)
    msg = format_kickoff_message(session)

    # Broadcast to all flatmates opted into notifications
    members = db.query(Member).filter(Member.is_cook == False, Member.notify == True).all()
    sent_count = 0
    for m in members:
        p = m.whatsapp_phone or m.phone
        if p.strip():
            res = send_text(p.strip(), msg)
            if res.sent:
                sent_count += 1

    return f"Kickoff sent to {sent_count} flatmates for {session.target_date} ({session.meal_slot})"


def job_flat_hourly_nudge(db) -> str:
    """Checks hourly between 7:00 PM and 1:00 AM: if not locked, sends gentle nudge."""
    now = now_local()
    # Only active between 19:00 (7 PM) and 01:00 (1 AM)
    if not (19 <= now.hour <= 23 or now.hour == 0):
        return "Outside nudge hours (7 PM - 1 AM)"

    tomorrow = today() + timedelta(days=1)
    session = (
        db.query(FlatDecisionSession)
        .filter(FlatDecisionSession.target_date == tomorrow, FlatDecisionSession.stage != "locked")
        .order_by(FlatDecisionSession.id.desc())
        .first()
    )
    if not session:
        return "No pending meal decisions"

    # Increment nudge count
    session.nudge_count += 1
    session.last_nudge_at = now.replace(tzinfo=None)
    db.commit()

    nudge_msg = format_hourly_reminder(session)
    sent_count = 0
    if nudge_msg:
        members = db.query(Member).filter(Member.is_cook == False, Member.notify == True).all()
        for m in members:
            p = m.whatsapp_phone or m.phone
            if p.strip():
                res = send_text(p.strip(), nudge_msg)
                if res.sent:
                    sent_count += 1

    return f"Nudge #{session.nudge_count} sent to {sent_count} flatmates for {session.selected_recipe_name or 'meal choice'}"


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    timezone = get_settings().timezone
    scheduler = BackgroundScheduler(
        timezone=timezone,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
    )
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
    # 6:00 PM WhatsApp Group Evening Kickoff
    scheduler.add_job(
        lambda: _run(job_flat_evening_kickoff),
        CronTrigger(hour=18, minute=0, timezone=timezone),
        id="flat_evening_kickoff",
        replace_existing=True,
    )
    # Hourly Nudge at the top of every hour (7 PM to 1 AM)
    scheduler.add_job(
        lambda: _run(job_flat_hourly_nudge),
        CronTrigger(hour="19-23,0", minute=0, timezone=timezone),
        id="flat_hourly_nudge",
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
