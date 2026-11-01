import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe, Member
from app.services.flat_chat import (
    get_or_create_evening_session,
    format_kickoff_message,
    format_hourly_reminder,
    process_incoming_group_message,
    FlatDecisionSession,
)
from app.services.household import get_cook
from app.services.menu import upsert_meal
from app.services.voice import place_call
from app.services.timeutil import today, now_local

router = APIRouter(prefix="/api/flat-chat", tags=["flat-chat"])


@router.get("/session/today")
def get_current_session(db: Session = Depends(get_db)):
    """Get the active evening decision session for tomorrow."""
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)
    options = []
    try:
        options = json.loads(session.options_json)
    except Exception:
        options = []

    # Get cook details
    cook = get_cook(db)
    cook_name = cook.name if cook else "Cook"
    cook_phone = cook.phone if (cook and cook.phone) else ""

    # Get selected recipe details and ingredients
    selected_ingredients = []
    hindi_name = ""
    if session.selected_recipe_name:
        r = db.query(Recipe).filter(Recipe.name.ilike(session.selected_recipe_name)).first()
        if r:
            selected_ingredients = r.ingredients or []
            hindi_name = r.name_hi or ""

    # Generate natural Hindi speech script ready for the cook call
    dish_display = f"{session.selected_recipe_name} ({hindi_name})" if hindi_name else session.selected_recipe_name
    slot_hi = "रात के खाने" if session.meal_slot == "dinner" else "दोपहर के खाने"
    day_str = session.target_date.strftime("%d %B")

    if session.selected_recipe_name:
        default_script = (
            f"नमस्ते {cook_name}! कल {day_str} को {slot_hi} में {dish_display} बनाना तय हुआ है। "
            f"किचन में सारा सामान उपलब्ध है। कृपया समय पर आकर बना दें। धन्यवाद!"
        )
    else:
        default_script = (
            f"नमस्ते {cook_name}! कल {day_str} के खाने का मेनू अभी तय हो रहा है। धन्यवाद!"
        )

    return {
        "id": session.id,
        "target_date": session.target_date.isoformat(),
        "target_date_formatted": session.target_date.strftime("%A, %d %b %Y"),
        "meal_slot": session.meal_slot,
        "stage": session.stage,
        "selected_recipe_name": session.selected_recipe_name,
        "selected_recipe_hindi": hindi_name,
        "selected_ingredients": selected_ingredients,
        "options": options,
        "cook_name": cook_name,
        "cook_phone": cook_phone,
        "default_hindi_script": default_script,
        "nudge_count": session.nudge_count,
        "kickoff_text": format_kickoff_message(session),
        "reminder_text": format_hourly_reminder(session),
    }


@router.post("/vote")
async def cast_vote(request: Request, db: Session = Depends(get_db)):
    """Vote for an option or custom dish."""
    data = await request.json()
    dish_name = data.get("dish_name", "").strip()
    voter = data.get("voter", "Flatmate").strip()
    
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)

    if not dish_name:
        raise HTTPException(400, "Dish name is required")

    session.selected_recipe_name = dish_name
    session.stage = "waiting_grocery"
    db.commit()
    db.refresh(session)
    return {"ok": True, "selected_recipe_name": session.selected_recipe_name, "stage": session.stage}


@router.post("/lock")
async def lock_decision(db: Session = Depends(get_db)):
    """Lock the meal decision and sync to calendar."""
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)
    
    if not session.selected_recipe_name:
        # Default to option 1 if none picked
        try:
            opts = json.loads(session.options_json)
            if opts:
                session.selected_recipe_name = opts[0]["name"]
        except Exception:
            session.selected_recipe_name = "Poha"

    session.stage = "locked"
    
    # Match recipe ID if exists
    r = db.query(Recipe).filter(Recipe.name.ilike(session.selected_recipe_name)).first()
    recipe_id = r.id if r else None

    # Upsert to kitchen calendar
    upsert_meal(db, session.target_date, session.meal_slot, recipe_id=recipe_id, recipe_name=session.selected_recipe_name)
    db.commit()
    return {"ok": True, "stage": "locked", "selected_recipe_name": session.selected_recipe_name}


@router.post("/call-cook")
async def call_cook_now(request: Request, db: Session = Depends(get_db)):
    """Place an instant voice call to the cook with custom/editable Hindi script."""
    data = await request.json()
    custom_script = data.get("script", "").strip()
    phone = data.get("phone", "").strip()

    cook = get_cook(db)
    target_phone = phone or (cook.phone if cook else "")
    if not target_phone:
        raise HTTPException(400, "Cook has no phone number configured. Please add cook's phone in Household.")

    res = place_call(target_phone, custom_script)
    return {
        "ok": res.placed or res.status == "simulated",
        "status": res.status,
        "detail": res.detail,
        "provider_id": res.provider_id,
        "phone": target_phone,
    }


@router.post("/reset")
def reset_session(db: Session = Depends(get_db)):
    """Reset decision to choosing_meal so flatmates can re-vote."""
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)
    session.stage = "choosing_meal"
    session.selected_recipe_name = ""
    db.commit()
    return {"ok": True, "stage": "choosing_meal"}


@router.post("/message")
async def receive_group_message(request: Request, db: Session = Depends(get_db)):
    """Simulate or receive an incoming WhatsApp group message."""
    data = await request.json()
    text = data.get("text", "")
    sender = data.get("sender", "Flatmate")
    reply = process_incoming_group_message(db, text=text, sender_name=sender)
    return {"reply": reply}
