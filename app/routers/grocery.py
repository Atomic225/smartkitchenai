from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import NotificationOut, ShoppingListOut
from app.services.grocery import build_shopping_list, latest_list, toggle_item
from app.services.notify import list_notifications, send_grocery_reminders
from app.services.timeutil import monday_of, today

router = APIRouter(prefix="/api", tags=["grocery"])


@router.get("/grocery", response_model=ShoppingListOut | None)
def get_grocery(db: Session = Depends(get_db)):
    return latest_list(db)


@router.post("/grocery/rebuild", response_model=ShoppingListOut)
def rebuild(week_start: date | None = None, db: Session = Depends(get_db)):
    try:
        return build_shopping_list(db, monday_of(week_start or today()))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/grocery/items/{item_id}/purchased")
def purchased(item_id: int, purchased: bool = True, db: Session = Depends(get_db)):
    try:
        item = toggle_item(db, item_id, purchased)
    except KeyError as exc:
        raise HTTPException(404, "Item not found") from exc
    return {"id": item.id, "purchased": item.purchased}


@router.post("/grocery/reminders/run", response_model=list[NotificationOut])
def run_reminders(db: Session = Depends(get_db)):
    return send_grocery_reminders(db)


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db)):
    return list_notifications(db)
