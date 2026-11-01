from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import ChefCall
from app.services.household import get_cook, get_household
from app.services.menu import dish_name, meals_for_date
from app.services.timeutil import combine_local, now_local, today
from app.services.voice import place_call

SLOT_HI = {
    "breakfast": "Nashte mein",
    "brunch": "Brunch mein",
    "lunch": "Dopahar ke lunch mein",
    "evening_snack": "Shaam ke nashte mein",
    "dinner": "Raat ke dinner mein",
}


def build_script(db: Session, day: date, call_type: str = "daily") -> str:
    """Generate a polite, clear, natural Hindi voice script for the cook."""
    household = get_household(db)
    all_meals = meals_for_date(db, day)
    cook = get_cook(db)
    cook_name = (cook.name.strip() + " ") if (cook and cook.name.strip()) else ""

    # Filter meals based on call type
    if call_type == "weekend_lunch":
        target_meals = [m for m in all_meals if m.meal_slot in {"breakfast", "brunch", "lunch"}]
        greeting = f"Namaste {cook_name}bhaiya! Aaj weekend hai. Dopahar ke lunch ke liye menu yeh hai:"
        closing = f"Khana lagbhag {household.size} logon ke liye banana hai. Shaam ko dinner ke menu ke liye dobara call aayegi. Dhanyawad!"
    elif call_type == "weekend_dinner":
        target_meals = [m for m in all_meals if m.meal_slot in {"evening_snack", "dinner"}]
        greeting = f"Namaste {cook_name}bhaiya! Aaj raat ke dinner ka menu yeh hai:"
        closing = f"Khana lagbhag {household.size} logon ke liye tayar karna hai. Kripya samay par shuru kar dijiye. Dhanyawad!"
    else:  # weekday / daily
        target_meals = all_meals
        day_name = day.strftime("%A")
        day_hi = {
            "Monday": "Somvar",
            "Tuesday": "Mangalvar",
            "Wednesday": "Budhvar",
            "Thursday": "Guruvar",
            "Friday": "Shukravar",
            "Saturday": "Shanivar",
            "Sunday": "Ravivar",
        }.get(day_name, day_name)
        greeting = f"Namaste {cook_name}bhaiya! Aaj {day_hi} ka kitchen menu yeh hai:"
        closing = f"Khana lagbhag {household.size} logon ke liye banana hai. Kripya samay par shuru kar dijiye. Dhanyawad!"

    if not target_meals:
        return f"Namaste {cook_name}bhaiya! Aaj ka menu abhi set nahi hua hai. Kripya ghar walon se confirm kar lijiye. Dhanyawad!"

    lines = [greeting]
    for item in target_meals:
        slot_label = SLOT_HI.get(item.meal_slot, item.meal_slot.capitalize())
        name = dish_name(item)
        if item.recipe and item.recipe.name_hi:
            name = item.recipe.name_hi
        line = f"{slot_label}: {name}."
        if item.notes:
            line += f" Note: {item.notes}."
        lines.append(line)

    lines.append(closing)
    return " ".join(lines)


def schedule_calls_for_date(db: Session, day: date) -> list[ChefCall]:
    """Schedule the cook calls for a specific date:
    - Monday to Friday: 1 call (at chef_call_weekday_time).
    - Saturday & Sunday: 2 calls (Call 1 at weekend_lunch_time, Call 2 at weekend_dinner_time).
    """
    household = get_household(db)
    if not household.chef_call_enabled:
        return []
    cook = get_cook(db)
    if cook is None:
        return []

    is_weekend = day.weekday() >= 5  # 5=Saturday, 6=Sunday
    planned_slots: list[tuple[str, str]] = []

    if not is_weekend:
        # Monday to Friday: 1 call
        weekday_time = household.chef_call_weekday_time or household.chef_call_time or "08:30"
        planned_slots.append(("weekday", weekday_time))
    else:
        # Saturday and Sunday: 2 calls
        lunch_time = household.chef_call_weekend_lunch_time or "09:30"
        dinner_time = household.chef_call_weekend_dinner_time or "17:00"
        planned_slots.append(("weekend_lunch", lunch_time))
        planned_slots.append(("weekend_dinner", dinner_time))

    created_or_existing: list[ChefCall] = []
    for call_type, time_str in planned_slots:
        # Check if already scheduled or completed
        existing = (
            db.query(ChefCall)
            .filter(ChefCall.menu_date == day, ChefCall.call_type == call_type)
            .order_by(ChefCall.id.desc())
            .first()
        )
        if existing and existing.status in {"scheduled", "initiated", "completed", "confirmed"}:
            created_or_existing.append(existing)
            continue

        script = build_script(db, day, call_type)
        scheduled_dt = combine_local(day, time_str).replace(tzinfo=None)

        call = ChefCall(
            menu_date=day,
            call_type=call_type,
            cook_name=cook.name,
            cook_phone=cook.phone,
            script=script,
            scheduled_for=scheduled_dt,
            status="scheduled",
            max_attempts=3,
        )
        db.add(call)
        created_or_existing.append(call)

    db.commit()
    for call in created_or_existing:
        db.refresh(call)

    return created_or_existing


def schedule_call_for_date(db: Session, day: date) -> ChefCall | None:
    """Backward-compatible helper returning the primary scheduled call for the date."""
    calls = schedule_calls_for_date(db, day)
    return calls[0] if calls else None


def execute_call(db: Session, call: ChefCall) -> ChefCall:
    call.attempts += 1
    call.script = build_script(db, call.menu_date, getattr(call, "call_type", "daily"))
    result = place_call(call.cook_phone, call.script)
    call.updated_at = now_local().replace(tzinfo=None)
    if result.placed:
        call.status = "initiated"
        call.provider_call_id = result.provider_id
        call.error = ""
    else:
        call.status = result.status
        call.error = result.detail
        if call.attempts < call.max_attempts and result.status in {"failed", "no-answer"}:
            call.status = "retry_scheduled"
    db.commit()
    db.refresh(call)
    return call


def run_due_calls(db: Session) -> list[ChefCall]:
    household = get_household(db)
    if not household.chef_call_enabled:
        return []
    day = today()
    schedule_calls_for_date(db, day)
    due = (
        db.query(ChefCall)
        .filter(ChefCall.menu_date == day, ChefCall.status.in_(["scheduled", "retry_scheduled", "no-answer", "failed"]))
        .all()
    )
    now = now_local().replace(tzinfo=None)
    processed = []
    for call in due:
        scheduled = call.scheduled_for or now
        retry_ready = call.status in {"retry_scheduled", "no-answer", "failed"}
        if retry_ready and call.attempts > 0:
            wait_until = scheduled + timedelta(minutes=15 * call.attempts)
            if now < wait_until:
                continue
        elif now < scheduled:
            continue
        if call.attempts >= call.max_attempts and call.status not in {"scheduled"}:
            call.status = "gave_up"
            call.error = (call.error + " Max retries reached. Call was not completed.").strip()
            db.commit()
            processed.append(call)
            continue
        processed.append(execute_call(db, call))
    return processed


def mark_from_webhook(db: Session, provider_id: str, status: str, response_text: str = "") -> ChefCall | None:
    call = db.query(ChefCall).filter(ChefCall.provider_call_id == provider_id).order_by(ChefCall.id.desc()).first()
    if call is None:
        return None
    mapping = {
        "completed": "completed",
        "answered": "completed",
        "busy": "no-answer",
        "no-answer": "no-answer",
        "failed": "failed",
        "canceled": "failed",
    }
    call.status = mapping.get(status.lower(), status.lower())
    if response_text:
        call.response_text = response_text
        lowered = response_text.lower()
        if any(word in lowered for word in ("haan", "han", "yes", "samajh")):
            call.status = "confirmed"
        elif any(word in lowered for word in ("nahi", "no")):
            call.status = "rejected"
    db.commit()
    db.refresh(call)
    return call


def list_calls(db: Session, limit: int = 50) -> list[ChefCall]:
    return db.query(ChefCall).order_by(ChefCall.id.desc()).limit(limit).all()
