from __future__ import annotations

from datetime import datetime, date, time
from typing import Any
import json
import re

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.database import Base
from app.models import Recipe, WeeklyMenu, MenuItem, ShoppingList, ShoppingItem
from app.schemas import MenuItemIn
from app.services.household import get_household
from app.services.menu import dish_name, meals_for_date, upsert_meal
from app.services.grocery import build_shopping_list
from app.services.timeutil import today, now_local


class FlatDecisionSession(Base):
    __tablename__ = "flat_decision_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(40))  # "dinner" on Mon-Fri, "lunch" on Sat-Sun
    stage: Mapped[str] = mapped_column(String(40), default="choosing_meal")
    # Stages:
    # "choosing_meal"     -> 4 options presented, waiting for a pick or change
    # "waiting_grocery"   -> meal picked, waiting for groceries to be ordered
    # "confirming_order"  -> flatmate said ordered, AI asks for final confirmation
    # "locked"            -> confirmed and locked! (or past 1 AM cutoff)

    options_json: Mapped[str] = mapped_column(Text, default="[]")  # list of recipe IDs/names
    selected_recipe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_recipe_name: Mapped[str] = mapped_column(String(160), default="")
    
    last_nudge_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nudge_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def get_or_create_evening_session(db: Session, target_day: date) -> FlatDecisionSession:
    """Find or initialize the evening decision session for target_day.
    Mon-Fri: Tomorrow's Dinner
    Sat-Sun: Tomorrow's Lunch
    """
    # Check weekday of target_day: 5=Saturday, 6=Sunday
    is_weekend = target_day.weekday() >= 5
    slot = "lunch" if is_weekend else "dinner"

    session = (
        db.query(FlatDecisionSession)
        .filter(FlatDecisionSession.target_date == target_day, FlatDecisionSession.meal_slot == slot)
        .order_by(FlatDecisionSession.id.desc())
        .first()
    )
    if session:
        return session

    # Pick 4 recipe options suitable for this slot
    recipes = db.query(Recipe).all()
    # Filter or select 4 diverse recipes
    selected_options = []
    for r in recipes[:4]:
        selected_options.append({"id": r.id, "name": r.name, "name_hi": r.name_hi})

    session = FlatDecisionSession(
        target_date=target_day,
        meal_slot=slot,
        stage="choosing_meal",
        options_json=json.dumps(selected_options),
        last_nudge_at=now_local().replace(tzinfo=None),
        nudge_count=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def format_kickoff_message(session: FlatDecisionSession) -> str:
    """Format the 6:00 PM kickoff message in English."""
    day_name = session.target_date.strftime("%A, %d %b")
    slot_title = session.meal_slot.capitalize()
    options = json.loads(session.options_json)

    lines = [
        f"👋 *Hey Flatmates!*",
        f"Time to decide tomorrow's *{slot_title}* ({day_name})! 🍽️",
        "",
        "Here are 4 options from our kitchen:",
    ]
    for idx, opt in enumerate(options, 1):
        hi_suffix = f" ({opt['name_hi']})" if opt.get("name_hi") else ""
        lines.append(f"*{idx}.* {opt['name']}{hi_suffix}")

    lines.extend([
        "",
        "💬 *Reply with your choice* (e.g. `Option 2` or `Paneer`).",
        "_Note: Anyone can change their mind anytime until groceries are confirmed!_",
    ])
    return "\n".join(lines)


def format_hourly_reminder(session: FlatDecisionSession) -> str:
    """Format gentle hourly nudges between 6:00 PM and 1:00 AM in English."""
    slot_title = session.meal_slot.capitalize()
    options = json.loads(session.options_json)

    if session.stage == "choosing_meal":
        lines = [
            f"🔔 *Friendly Reminder!*",
            f"We haven't picked tomorrow's *{slot_title}* yet. Which one sounds good?",
        ]
        for idx, opt in enumerate(options, 1):
            lines.append(f"{idx}. {opt['name']}")
        lines.append("\n_Just reply with the number or dish name!_")
        return "\n".join(lines)

    elif session.stage == "waiting_grocery":
        return (
            f"🛒 *Grocery Check:* Tomorrow's {slot_title} is set to *{session.selected_recipe_name}*.\n"
            f"Has anyone ordered the groceries from Zepto/Blinkit/Instamart yet?\n\n"
            f"👉 Reply *'Ordered'* or *'Done'* once placed!"
        )

    elif session.stage == "confirming_order":
        return (
            f"⚠️ *Confirmation Pending:*\n"
            f"Should I lock in the groceries for *{session.selected_recipe_name}*?\n"
            f"👉 Reply *'Yes, lock it'* to confirm, or change the dish now!"
        )

    return ""


def process_incoming_group_message(db: Session, text: str, sender_name: str = "") -> str:
    """Process incoming flatmate message in English and advance the state machine."""
    text_clean = text.strip().lower()
    now = now_local()

    # Find the active unclosed session (or today's/tomorrow's evening session)
    session = (
        db.query(FlatDecisionSession)
        .filter(FlatDecisionSession.stage != "locked")
        .order_by(FlatDecisionSession.id.desc())
        .first()
    )
    if not session:
        return "No active meal vote right now. The daily menu check starts at 6:00 PM!"

    options = json.loads(session.options_json)
    household = get_household(db)

    # 1. State: Confirming final lock
    if session.stage == "confirming_order":
        if any(w in text_clean for w in ["yes", "lock", "confirm", "haan", "sure", "done"]):
            session.stage = "locked"
            session.updated_at = now.replace(tzinfo=None)
            
            # Apply meal to database calendar
            if session.selected_recipe_id:
                upsert_meal(
                    db,
                    MenuItemIn(
                        meal_date=session.target_date,
                        meal_slot=session.meal_slot,
                        recipe_id=session.selected_recipe_id,
                    ),
                )
                build_shopping_list(db, session.target_date)

            db.commit()

            chef_time = household.chef_call_weekday_time or "08:30"
            return (
                f"🔒 *Locked & Confirmed!* 🎉\n\n"
                f"Tomorrow's {session.meal_slot.capitalize()} is officially *{session.selected_recipe_name}*.\n"
                f"No further changes can be made because groceries are marked as ordered.\n\n"
                f"📞 I will automatically call our cook at *{chef_time} AM* with the Hindi menu instructions. Good night, flatmates! ✨"
            )
        elif any(w in text_clean for w in ["no", "wait", "cancel", "change"]):
            session.stage = "waiting_grocery"
            db.commit()
            return f"Understood! Order confirmation cancelled. You can still change tomorrow's {session.meal_slot} or confirm later."

    # 2. State: Waiting for grocery order
    if session.stage in {"waiting_grocery", "choosing_meal"}:
        if any(w in text_clean for w in ["ordered", "order done", "kar diya", "bought", "got it"]):
            session.stage = "confirming_order"
            db.commit()
            return (
                f"Awesome, thanks {sender_name or 'buddy'}! 👍\n\n"
                f"Can you confirm: *Are the groceries for {session.selected_recipe_name} officially on the way?*\n"
                f"_(Once you say 'Yes', the menu cannot be changed)._"
            )

    # 3. Flatmate choosing or changing the dish
    # Check option numbers (1 to 4)
    chosen_opt = None
    num_match = re.search(r"\b([1-4])\b", text_clean)
    if num_match:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(options):
            chosen_opt = options[idx]

    # Or match by recipe name substring
    if not chosen_opt:
        for opt in options:
            if opt["name"].lower() in text_clean or (opt.get("name_hi") and opt["name_hi"].lower() in text_clean):
                chosen_opt = opt
                break

    if chosen_opt:
        previous_dish = session.selected_recipe_name
        session.selected_recipe_id = chosen_opt["id"]
        session.selected_recipe_name = chosen_opt["name"]
        session.stage = "waiting_grocery"
        session.updated_at = now.replace(tzinfo=None)
        db.commit()

        if previous_dish and previous_dish != chosen_opt["name"]:
            return (
                f"🔄 *Menu Updated by {sender_name or 'someone'}!*\n\n"
                f"Changed tomorrow's {session.meal_slot} from ~{previous_dish}~ to *{chosen_opt['name']}* 🍲.\n\n"
                f"Remember, anyone can still change this until groceries are ordered.\n"
                f"👉 Let the group know once you place the grocery order!"
            )
        else:
            return (
                f"✅ *Selected: {chosen_opt['name']}* 🍲\n\n"
                f"Tomorrow's {session.meal_slot} is set to *{chosen_opt['name']}*.\n"
                f"Anyone can change this until groceries are ordered.\n"
                f"👉 Please order groceries and reply *'Ordered'* when done!"
            )

    return ""
