from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import JobRun
from app.services.chef import run_due_calls, schedule_calls_for_date
from app.services.grocery import build_shopping_list
from app.services.household import get_household
from app.services.menu import generate_weekly_menu, get_week
from app.services.notify import catch_up_pending_reminders, send_grocery_reminders
from app.services.timeutil import monday_of, next_or_current_week_start, now_local, today, week_bounds


def _begin_run(db: Session, job_name: str, run_key: str) -> JobRun | None:
    row = JobRun(job_name=job_name, run_key=run_key, status="running")
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        return None


def _finish(db: Session, row: JobRun, status: str, details: str) -> None:
    row.status = status
    row.details = details[:4000]
    db.commit()


def job_generate_weekly_menu(db: Session, force: bool = False) -> str:
    household = get_household(db)
    if not household.auto_weekly_menu and not force:
        return "skipped: auto weekly menu disabled"
    local = now_local()
    # Sunday generation, plus startup catch-up if this week's menu is missing after Sunday.
    if local.weekday() != 6 and not force:
        current_start, _ = week_bounds(local.date())
        if get_week(db, current_start) is not None:
            return "skipped: not Sunday and current week already exists"
        if local.weekday() == 0 and local.hour < 10:
            start = current_start
        else:
            return "skipped: not Sunday"
    else:
        start = next_or_current_week_start() if local.weekday() == 6 else monday_of(local.date())

    run_key = start.isoformat()
    if not force:
        claimed = _begin_run(db, "weekly_menu", run_key)
        if claimed is None:
            return f"skipped duplicate weekly_menu {run_key}"
    else:
        claimed = _begin_run(db, "weekly_menu_manual", f"{run_key}:{now_local().isoformat()}")
    try:
        menu = generate_weekly_menu(db, start, source="scheduler" if not force else "manual")
        groceries = build_shopping_list(db, menu.week_start)
        details = f"menu_id={menu.id} meals={len(menu.items)} grocery_items={len(groceries.items)}"
        if claimed:
            _finish(db, claimed, "success", details)
        return details
    except Exception as exc:  # noqa: BLE001
        if claimed:
            _finish(db, claimed, "error", str(exc))
        raise


def job_grocery_reminders(db: Session) -> str:
    run_key = today().isoformat()
    claimed = _begin_run(db, "grocery_reminders_tick", run_key)
    # Hourly ticks share one run_key per day for catch-up bookkeeping, but
    # per-recipient notification idempotency is the real duplicate guard.
    notes = send_grocery_reminders(db)
    extra = catch_up_pending_reminders(db)
    merged = {row.id: row for row in notes + extra}
    summary = ", ".join(f"{row.recipient_name}:{row.status}" for row in merged.values()) or "nothing due"
    if claimed:
        _finish(db, claimed, "success", summary)
    else:
        existing = db.query(JobRun).filter(JobRun.job_name == "grocery_reminders_tick", JobRun.run_key == run_key).first()
        if existing:
            existing.details = summary
            existing.status = "success"
            db.commit()
    return summary


def job_chef_calls(db: Session) -> str:
    tomorrow = today() + timedelta(days=1)
    schedule_calls_for_date(db, today())
    schedule_calls_for_date(db, tomorrow)
    processed = run_due_calls(db)
    if not processed:
        return "no due chef calls"
    return ", ".join(f"{row.menu_date}:{getattr(row, 'call_type', 'call')}:{row.status}" for row in processed)


def recent_job_runs(db: Session, limit: int = 20) -> list[dict]:
    rows = db.query(JobRun).order_by(JobRun.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "job_name": row.job_name,
            "run_key": row.run_key,
            "status": row.status,
            "details": row.details,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
