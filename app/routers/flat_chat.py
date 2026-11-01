from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.flat_chat import (
    get_or_create_evening_session,
    format_kickoff_message,
    format_hourly_reminder,
    process_incoming_group_message,
    FlatDecisionSession,
)
from app.services.timeutil import today, now_local

router = APIRouter(prefix="/api/flat-chat", tags=["flat-chat"])


@router.get("/session/today")
def get_current_session(db: Session = Depends(get_db)):
    """Get the active evening decision session for tomorrow."""
    tomorrow = today() + timedelta(days=1)
    session = get_or_create_evening_session(db, tomorrow)
    return {
        "id": session.id,
        "target_date": session.target_date.isoformat(),
        "meal_slot": session.meal_slot,
        "stage": session.stage,
        "selected_recipe_name": session.selected_recipe_name,
        "nudge_count": session.nudge_count,
        "kickoff_text": format_kickoff_message(session),
        "reminder_text": format_hourly_reminder(session),
    }


@router.post("/message")
async def receive_group_message(request: Request, db: Session = Depends(get_db)):
    """Simulate or receive an incoming WhatsApp group message."""
    data = await request.json()
    text = data.get("text", "")
    sender = data.get("sender", "Flatmate")
    reply = process_incoming_group_message(db, text=text, sender_name=sender)
    return {"reply": reply}
