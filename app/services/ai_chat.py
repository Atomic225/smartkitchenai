from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ChatMessage, Recipe
from app.schemas import MenuItemIn
from app.services.grocery import build_shopping_list
from app.services.household import add_member, get_household
from app.services.menu import SLOT_ORDER, delete_meal, delete_week, find_recipe, generate_weekly_menu, get_week, meals_for_date, serialize_item, upsert_meal
from app.services.timeutil import monday_of, today, week_bounds
from app.schemas import MemberIn


def _json_safe(obj):
    """Recursively convert date/datetime objects to ISO strings for JSON storage."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj

DAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "somvar": 0,
    "mangal": 1,
    "mangalwar": 1,
    "budh": 2,
    "budhwar": 2,
    "guru": 3,
    "guruwar": 3,
    "shukra": 4,
    "shukrawar": 4,
    "shani": 5,
    "shanivar": 5,
    "ravi": 6,
    "ravivar": 6,
    "aaj": -1,
    "today": -1,
    "kal": -2,
    "tomorrow": -2,
}

SLOTS = {
    "breakfast": "breakfast",
    "nashta": "breakfast",
    "naashta": "breakfast",
    "brunch": "brunch",
    "lunch": "lunch",
    "dopahar": "lunch",
    "dinner": "dinner",
    "raat": "dinner",
    "shaam": "evening_snack",
    "snack": "evening_snack",
    "evening_snack": "evening_snack",
    "nasta": "evening_snack",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_weekly_menu",
            "description": "Create or regenerate a full weekly menu starting on a Monday.",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {"type": "string", "description": "Monday date YYYY-MM-DD. Empty = current/next planning week."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_meal",
            "description": "Create or replace a meal on a specific date and slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_date": {"type": "string"},
                    "meal_slot": {"type": "string", "enum": ["breakfast", "brunch", "lunch", "evening_snack", "dinner"]},
                    "dish": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["meal_date", "meal_slot", "dish"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_meal",
            "description": "Delete one meal slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_date": {"type": "string"},
                    "meal_slot": {"type": "string"},
                },
                "required": ["meal_date", "meal_slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_weekly_menu",
            "description": "Delete an entire weekly menu.",
            "parameters": {"type": "object", "properties": {"week_start": {"type": "string"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_menu",
            "description": "Show meals for one date when meal_date is supplied; otherwise show the latest saved weekly menu. For a specific week, supply week_start as YYYY-MM-DD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_date": {"type": "string", "description": "Optional specific meal date YYYY-MM-DD."},
                    "week_start": {"type": "string", "description": "Optional date in the week to retrieve; defaults to the latest saved week."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rebuild_grocery_list",
            "description": "Rebuild the consolidated grocery list from a saved weekly menu. Optionally specify a date within that week.",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {"type": "string", "description": "Optional date within the menu week, YYYY-MM-DD. Defaults to the latest saved menu week."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recipes",
            "description": "List known dishes the kitchen can cook.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_household_member",
            "description": "Add a household member.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "is_cook": {"type": "boolean"},
                    "notify": {"type": "boolean"},
                },
                "required": ["name"],
            },
        },
    },
]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip().lower()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    if value in DAYS:
        code = DAYS[value]
        if code == -1:
            return today()
        if code == -2:
            return today() + timedelta(days=1)
        start, _ = week_bounds(today())
        return start + timedelta(days=code)
    for name, code in DAYS.items():
        if name in value:
            start, _ = week_bounds(today())
            if code >= 0:
                return start + timedelta(days=code)
            if code == -1:
                return today()
            return today() + timedelta(days=1)
    return None


def _slot_from_text(text: str) -> str | None:
    lowered = text.lower()
    for key, slot in SLOTS.items():
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            return slot
    return None


def openai_status() -> dict:
    settings = get_settings()
    configured = settings.openai_configured()
    return {
        "name": "OpenAI",
        "configured": configured,
        "mode": "live" if configured else "offline_parser",
        "detail": (
            f"Using {settings.openai_model} for English and Hinglish understanding."
            if configured
            else "OPENAI_API_KEY missing. A built-in English/Hinglish parser is used instead of GPT."
        ),
        "required_fields": ["OPENAI_API_KEY"],
    }


def _history(db: Session, limit: int = 12) -> list[ChatMessage]:
    rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit).all()
    return list(reversed(rows))


def _save(db: Session, role: str, content: str, intent: dict | None = None) -> None:
    db.add(ChatMessage(role=role, content=content, intent=_json_safe(intent) if intent is not None else None))
    db.commit()


def _tool_generate(db: Session, week_start: str | None = None) -> dict:
    start = _parse_date(week_start) if week_start else monday_of(today())
    menu = generate_weekly_menu(db, start, source="chat")
    try:
        build_shopping_list(db, menu.week_start)
    except ValueError:
        pass
    return {"ok": True, "week_start": str(menu.week_start), "meals": len(menu.items)}


def _tool_set_meal(db: Session, meal_date: str, meal_slot: str, dish: str, notes: str = "") -> dict:
    day = _parse_date(meal_date)
    if day is None:
        return {"ok": False, "error": "Could not understand the date."}
    recipe = find_recipe(db, dish)
    item = upsert_meal(
        db,
        MenuItemIn(
            meal_date=day,
            meal_slot=meal_slot,
            recipe_id=recipe.id if recipe else None,
            custom_name="" if recipe else dish,
            notes=notes or "",
        ),
    )
    try:
        week = get_week(db, day)
        if week:
            build_shopping_list(db, week.week_start)
    except ValueError:
        pass
    return {"ok": True, "item": serialize_item(item), "matched_recipe": bool(recipe)}


def _tool_delete_meal(db: Session, meal_date: str, meal_slot: str) -> dict:
    day = _parse_date(meal_date)
    if day is None:
        return {"ok": False, "error": "Could not understand the date."}
    deleted = delete_meal(db, day, meal_slot)
    return {"ok": deleted, "meal_date": str(day), "meal_slot": meal_slot}


def _tool_delete_week(db: Session, week_start: str | None = None) -> dict:
    start = _parse_date(week_start) if week_start else monday_of(today())
    if start is None:
        return {"ok": False, "error": "Could not understand the week."}
    return {"ok": delete_week(db, start), "week_start": str(monday_of(start))}


def _tool_show_menu(
    db: Session,
    meal_date: str | None = None,
    week_start: str | None = None,
) -> dict:
    """Read one day's meals or the latest/specified saved weekly menu."""
    if meal_date:
        day = _parse_date(meal_date)
        if day is None:
            return {"ok": False, "error": "Could not understand the meal date.", "meals": []}
        meals = meals_for_date(db, day)
        return {"date": day.isoformat(), "meals": [serialize_item(item) for item in meals]}

    reference = _parse_date(week_start) if week_start else None
    if week_start and reference is None:
        return {"ok": False, "error": "Could not understand the week date.", "meals": []}
    menu = get_week(db, reference)
    if menu is None:
        return {"ok": False, "week_start": None, "week_end": None, "meals": [], "message": "No saved weekly menu was found."}
    items = sorted(
        menu.items,
        key=lambda item: (
            item.meal_date,
            SLOT_ORDER.index(item.meal_slot) if item.meal_slot in SLOT_ORDER else 99,
        ),
    )
    return {
        "ok": True,
        "week_start": menu.week_start.isoformat(),
        "week_end": menu.week_end.isoformat(),
        "status": menu.status,
        "meals": [serialize_item(item) for item in items],
    }


def _tool_grocery(db: Session, week_start: str | None = None) -> dict:
    """Rebuild groceries for the requested week or the latest saved week."""
    reference = _parse_date(week_start) if week_start else None
    if week_start and reference is None:
        return {"ok": False, "error": "Could not understand the week date."}
    menu = get_week(db, reference)
    if menu is None:
        return {"ok": False, "error": "No saved weekly menu was found."}
    listing = build_shopping_list(db, menu.week_start)
    return {"ok": True, "week_start": menu.week_start.isoformat(), "items": len(listing.items)}


def _tool_recipes(db: Session, query: str | None = None) -> dict:
    recipes = db.query(Recipe).order_by(Recipe.name.asc()).all()
    if query:
        q = query.lower()
        recipes = [r for r in recipes if q in r.name.lower() or q in (r.name_hi or "").lower()]
    return {"recipes": [{"id": r.id, "name": r.name, "name_hi": r.name_hi} for r in recipes[:30]]}


def _tool_add_member(db: Session, name: str, phone: str = "", is_cook: bool = False, notify: bool = True) -> dict:
    member = add_member(
        db,
        MemberIn(name=name, phone=phone, whatsapp_phone=phone, is_cook=is_cook, notify=notify, role="cook" if is_cook else "member"),
    )
    return {"ok": True, "id": member.id, "name": member.name}


MUTATING_TOOLS = {
    "generate_weekly_menu",
    "set_meal",
    "delete_meal",
    "delete_weekly_menu",
    "rebuild_grocery_list",
    "add_household_member",
}


def _is_read_only_request(text: str) -> bool:
    """Detect explicit read-only/preview instructions before executing tools."""
    lowered = text.lower().replace("’", "'")
    read_only_phrases = (
        "do not modify", "don't modify", "do not change", "don't change",
        "without modifying", "without changing", "read only", "read-only",
        "do not save", "don't save", "not save", "until i approve",
        "until i confirm", "preview only", "just show", "only show",
    )
    return any(phrase in lowered for phrase in read_only_phrases)


HANDLERS: dict[str, Callable[..., dict]] = {
    "generate_weekly_menu": _tool_generate,
    "set_meal": _tool_set_meal,
    "delete_meal": _tool_delete_meal,
    "delete_weekly_menu": _tool_delete_week,
    "show_menu": _tool_show_menu,
    "rebuild_grocery_list": _tool_grocery,
    "list_recipes": _tool_recipes,
    "add_household_member": _tool_add_member,
}


def _run_tool(db: Session, name: str, arguments: dict[str, Any]) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"ok": False, "error": f"Unknown action {name}"}
    try:
        return handler(db, **{k: v for k, v in arguments.items() if v is not None})
    except TypeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _system_prompt(db: Session) -> str:
    household = get_household(db)
    recipes = ", ".join(r.name for r in db.query(Recipe).order_by(Recipe.name.asc()).all())
    return (
        "You are Smart Kitchen AI, a household kitchen manager for an Indian home. "
        "Understand English and Hinglish. Be concise and practical. "
        f"Household size is {household.size}. Timezone is Asia/Kolkata. "
        "Use show_menu without meal_date to read the latest saved weekly menu; use meal_date only for a single day. "
        "Use tools to create, edit, or delete meal plans only when the user clearly asks for that change. "
        "Never mutate data when the user asks to show, inspect, preview, or explain something, or explicitly says not to modify anything. "
        "Never delete an entire weekly menu unless the user explicitly requests deletion of that entire week. "
        "If the user asks for a draft or says not to save until approval, provide a draft in chat and do not call a mutating tool. "
        "If the user request is missing a day or a meal slot, ask a short clarification question instead of guessing. "
        "Do not claim WhatsApp messages or phone calls were sent unless a tool result says sent/initiated. "
        f"Known dishes: {recipes}."
    )


def _offline_handle(db: Session, text: str) -> tuple[str, bool, list[dict]]:
    lowered = text.lower()
    actions: list[dict] = []

    if any(word in lowered for word in ("recipe", "dishes", "kya bana sakte", "menu options")):
        result = _tool_recipes(db, None)
        actions.append({"name": "list_recipes", "result": result})
        names = ", ".join(item["name"] for item in result["recipes"][:12])
        return f"Known dishes include: {names}.", False, actions

    if any(phrase in lowered for phrase in ("grocery", "shopping list", "sabzi list", "bazaar")):
        try:
            result = _tool_grocery(db)
            actions.append({"name": "rebuild_grocery_list", "result": result})
            return f"Shopping list rebuilt with {result['items']} consolidated ingredients, scaled for household size.", False, actions
        except Exception as exc:  # noqa: BLE001
            return f"I could not rebuild groceries yet: {exc}", False, actions

    if any(phrase in lowered for phrase in ("delete week", "hafta delete", "poora menu hatao", "remove this week's menu")):
        result = _tool_delete_week(db, None)
        actions.append({"name": "delete_weekly_menu", "result": result})
        return "Deleted this week's menu." if result["ok"] else "No weekly menu was found to delete.", False, actions

    if any(phrase in lowered for phrase in ("generate", "bana do menu", "hafta ka menu", "weekly menu", "is hafte", "next week")) and any(
        word in lowered for word in ("menu", "week", "hafte", "hafta")
    ):
        result = _tool_generate(db, None)
        actions.append({"name": "generate_weekly_menu", "result": result})
        return (
            f"I created a weekly menu starting {result['week_start']} with {result['meals']} meals. "
            "Weekdays and weekends use different meal slots. You can edit any dish.",
            False,
            actions,
        )

    if any(word in lowered for word in ("show", "dikhao", "kya hai", "today's menu", "aaj ka menu", "kal ka")):
        day = _parse_date(lowered) or today()
        result = _tool_show_menu(db, day.isoformat())
        actions.append({"name": "show_menu", "result": result})
        if not result["meals"]:
            return f"No meals are saved for {result['date']}. Say 'is hafte ka menu banao' to generate a week.", False, actions
        lines = [f"Menu for {result['date']}:"]
        for meal in result["meals"]:
            lines.append(f"- {meal['meal_slot']}: {meal['dish_name']}")
        return "\n".join(lines), False, actions

    member_match = re.search(r"add (?:member|cook|chef)?\s*([a-zA-Z ]+)(?:\s+(\+?\d{10,15}))?", text, re.I)
    if "add" in lowered and any(word in lowered for word in ("member", "cook", "chef")) and member_match:
        name = member_match.group(1).strip()
        phone = (member_match.group(2) or "").strip()
        is_cook = "cook" in lowered or "chef" in lowered
        result = _tool_add_member(db, name=name, phone=phone, is_cook=is_cook)
        actions.append({"name": "add_household_member", "result": result})
        return f"Added {result['name']} to the household.", False, actions

    delete_intent = any(word in lowered for word in ("delete", "remove", "hatao", "hata do", "cancel"))
    day = _parse_date(lowered)
    slot = _slot_from_text(lowered)

    if delete_intent:
        if not day or not slot:
            return "Kaunsi din aur kaunsi meal hataun? Example: Friday dinner hatao.", True, actions
        result = _tool_delete_meal(db, day.isoformat(), slot)
        actions.append({"name": "delete_meal", "result": result})
        return (
            f"Removed {slot} on {day.isoformat()}."
            if result["ok"]
            else f"No {slot} was found on {day.isoformat()}."
        ), False, actions

    set_intent = any(word in lowered for word in ("banao", "bana do", "set", "change", "replace", "update", "ko ", "rakho"))
    if set_intent:
        if not day or not slot:
            return "Din aur meal slot dono chahiye. Example: Monday lunch ko paneer butter masala rakh do.", True, actions
        dish = text
        for token in list(DAYS) + list(SLOTS) + ["ko", "banao", "bana do", "rakh", "rakho", "set", "change", "to", "please", "kar do"]:
            dish = re.sub(rf"\b{re.escape(token)}\b", " ", dish, flags=re.I)
        dish = re.sub(r"\s+", " ", dish).strip(" .")
        if len(dish) < 3:
            return f"{day.strftime('%A')} {slot} pe kya banaun? Dish ka naam batao.", True, actions
        result = _tool_set_meal(db, day.isoformat(), slot, dish)
        actions.append({"name": "set_meal", "result": result})
        matched = "matched a recipe" if result.get("matched_recipe") else "saved as a custom dish"
        return f"Updated {day.strftime('%A')} {slot} to {result['item']['dish_name']} ({matched}).", False, actions

    return (
        "Main kitchen manager hoon. Aap English ya Hinglish mein bol sakte ho. "
        "Try: 'is hafte ka menu banao', 'Monday lunch ko rajma rakh do', 'Friday dinner hatao', "
        "or 'aaj ka menu dikhao'.",
        False,
        actions,
    )


def _gemini_handle(db: Session, text: str) -> tuple[str, bool, list[dict], bool]:
    """Call Gemini via Google's OpenAI-compatible endpoint with full tool-calling."""
    from openai import OpenAI  # openai SDK works against any OpenAI-compatible endpoint

    settings = get_settings()
    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=45.0,
        max_retries=1,
    )
    model = settings.gemini_model

    messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt(db)}]
    history = _history(db)
    # chat() saves the incoming user message before calling this handler. Remove
    # that newest row from history so the current prompt is sent exactly once.
    if history and history[-1].role == "user" and history[-1].content == text:
        history = history[:-1]
    for row in history:
        if row.role in {"user", "assistant"}:
            messages.append({"role": row.role, "content": row.content})
    messages.append({"role": "user", "content": text})

    actions: list[dict] = []
    for _ in range(6):  # allow more loops for multi-step tool chains
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            # Gemini 3.x models expect their default sampling settings.
            # Sending temperature can trigger HTTP 400 on newer model generations.
        )
        choice = response.choices[0]
        message = choice.message
        if message.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [],
            }
            for call in message.tool_calls:
                call_dict = {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                extra = getattr(call, "extra_content", None)
                if extra:
                    call_dict["extra_content"] = extra
                assistant_msg["tool_calls"].append(call_dict)
            messages.append(assistant_msg)
            read_only = _is_read_only_request(text)
            for call in message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                if read_only and call.function.name in MUTATING_TOOLS:
                    result = {
                        "ok": False,
                        "error": "This request is read-only. No kitchen data was changed.",
                    }
                else:
                    result = _run_tool(db, call.function.name, args)
                actions.append({"name": call.function.name, "arguments": args, "result": result})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(_json_safe(result))})
            continue
        reply = (message.content or "").strip()
        needs = "?" in reply and any(
            word in reply.lower() for word in ("which", "kaunsi", "clarify", "batao", "specify", "din", "meal")
        )
        return reply, needs, actions, True
    return "I updated the kitchen records. Ask me if you want the menu read back.", False, actions, True


def ai_status() -> dict:
    """Integration status for the AI provider shown in the dashboard."""
    settings = get_settings()
    if settings.gemini_configured():
        return {
            "name": "Google Gemini AI",
            "configured": True,
            "mode": "live",
            "detail": f"Using {settings.gemini_model} via Google OpenAI-compatible endpoint.",
            "required_fields": ["GEMINI_API_KEY"],
        }
    if settings.openai_configured():
        return {
            "name": "OpenAI (legacy)",
            "configured": True,
            "mode": "live",
            "detail": f"Using {settings.openai_model} (OpenAI). Set GEMINI_API_KEY to use Gemini instead.",
            "required_fields": ["OPENAI_API_KEY"],
        }
    return {
        "name": "AI Provider",
        "configured": False,
        "mode": "offline_parser",
        "detail": (
            "GEMINI_API_KEY not set. A built-in English/Hinglish parser is used instead of Gemini AI. "
            "Add your key on the Settings page."
        ),
        "required_fields": ["GEMINI_API_KEY"],
    }


# Keep legacy name so any code that imports openai_status still works
openai_status = ai_status


def chat(db: Session, text: str) -> dict:
    text = text.strip()
    _save(db, "user", text)
    settings = get_settings()
    used_ai = False

    if settings.gemini_configured():
        # Primary: Google Gemini via OpenAI-compatible API
        try:
            reply, needs, actions, used_ai = _gemini_handle(db, text)
        except Exception as exc:  # noqa: BLE001
            fallback, needs, actions = _offline_handle(db, text)
            reply = (
                f"Gemini call failed ({exc}). I used the offline English/Hinglish parser instead.\n\n{fallback}"
            )
            used_ai = False
    elif settings.openai_configured():
        # Fallback: legacy OpenAI key (uses same _gemini_handle logic but with OpenAI base URL)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt(db)}]
            for row in _history(db):
                if row.role in {"user", "assistant"}:
                    messages.append({"role": row.role, "content": row.content})
            messages.append({"role": "user", "content": text})
            actions: list[dict] = []
            for _ in range(4):
                response = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                )
                choice = response.choices[0]
                message = choice.message
                if message.tool_calls:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [
                                {
                                    "id": call.id,
                                    "type": "function",
                                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                                }
                                for call in message.tool_calls
                            ],
                        }
                    )
                    for call in message.tool_calls:
                        args = json.loads(call.function.arguments or "{}")
                        result = _run_tool(db, call.function.name, args)
                        actions.append({"name": call.function.name, "arguments": args, "result": result})
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(_json_safe(result))})
                    continue
                reply = (message.content or "").strip()
                needs = "?" in reply and any(
                    word in reply.lower() for word in ("which", "kaunsi", "clarify", "batao", "specify", "din", "meal")
                )
                used_ai = True
                break
            else:
                reply = "I updated the kitchen records. Ask me if you want the menu read back."
                needs = False
                used_ai = True
        except Exception as exc:  # noqa: BLE001
            fallback, needs, actions = _offline_handle(db, text)
            reply = (
                f"OpenAI call failed ({exc}). I used the offline English/Hinglish parser instead.\n\n{fallback}"
            )
            used_ai = False
    else:
        reply, needs, actions = _offline_handle(db, text)

    _save(db, "assistant", reply, {"needs_clarification": needs, "actions": actions, "used_openai": used_ai})
    return {
        "reply": reply,
        "needs_clarification": needs,
        "actions": actions,
        "used_openai": used_ai,  # kept for API backwards-compat; True means any live AI was used
    }