from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import ChefCall
from app.services.exotel import place_call
from app.services.household import get_cook, get_household
from app.services.menu import dish_name, meals_for_date
from app.services.timeutil import combine_local, now_local, today


SLOT_HI = {
    "breakfast": "nashta",
    "brunch": "brunch",
    "lunch": "lunch",
    "evening_snack": "shaam ka nasta",
    "dinner": "dinner",
}


def build_script(db: Session, day: date) -> str:
    household = get_household(db)
    meals = meals_for_date(db, day)
    cook = get_cook(db)
    cook_name = cook.name if cook else "Chef"
    if household.chef_language == "hindi":
        greeting = f"Namaste {cook_name}. Aaj {day.strftime('%A')} ki menu yeh hai."
    else:
        greeting = f"Namaste {cook_name}. Aaj {day.strftime('%A')} ka menu yeh raha."
    if not meals:
        return greeting + " Menu abhi set nahi hua. Kripya ghar walon se confirm karein. Menu samajh aa gaya kya?"
    lines = [greeting]
    for item in meals:
        slot = SLOT_HI.get(item.meal_slot, item.meal_slot)
        recipe_line = ""
        if item.recipe and item.recipe.hindi_script:
            recipe_line = " " + item.recipe.hindi_script
        lines.append(f"{slot.title()}: {dish_name(item)}.{recipe_line}")
        if item.notes:
            lines.append(f"Note: {item.notes}")
    lines.append(f"Servings lagbhag {household.size} logon ke liye hain.")
    lines.append("Kripya confirm kijiye: menu samajh aa gaya? Haan ya nahi boliye.")
    return " ".join(lines)


def schedule_call_for_date(db: Session, day: date) -> ChefCall | None:
    household = get_household(db)
    if not household.chef_call_enabled:
        return None
    cook = get_cook(db)
    if cook is None:
        return None
    existing = db.query(ChefCall).filter(ChefCall.menu_date == day).order_by(ChefCall.id.desc()).first()
    if existing and existing.status in {"scheduled", "initiated", "completed", "confirmed"}:
        return existing
    call = ChefCall(
        menu_date=day,
        cook_name=cook.name,
        cook_phone=cook.phone,
        script=build_script(db, day),
        scheduled_for=combine_local(day, household.chef_call_time).replace(tzinfo=None),
        status="scheduled",
        max_attempts=3,
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def execute_call(db: Session, call: ChefCall) -> ChefCall:
    call.attempts += 1
    call.script = build_script(db, call.menu_date)
    result = place_call(call.cook_phone)
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
    schedule_call_for_date(db, day)
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


def list_calls(db: Session, limit: int = 30) -> list[ChefCall]:
    return db.query(ChefCall).order_by(ChefCall.id.desc()).limit(limit).all()
