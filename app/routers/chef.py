from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChefCall
from app.schemas import ChefCallOut
from app.services.chef import (
    build_script,
    execute_call,
    list_calls,
    mark_from_webhook,
    schedule_call_for_date,
    schedule_calls_for_date,
)
from app.services.household import get_cook, get_household
from app.services.timeutil import today
from app.services.voice import place_call

router = APIRouter(tags=["chef"])


@router.get("/api/chef-calls", response_model=list[ChefCallOut])
def calls(db: Session = Depends(get_db)):
    return list_calls(db)


@router.get("/api/chef-calls/preview")
def preview_scripts(day: date | None = None, db: Session = Depends(get_db)):
    target_day = day or today()
    is_weekend = target_day.weekday() >= 5
    cook = get_cook(db)
    household = get_household(db)
    return {
        "date": target_day.isoformat(),
        "is_weekend": is_weekend,
        "cook_name": cook.name if cook else "None",
        "cook_phone": cook.phone if cook else "",
        "weekday_time": household.chef_call_weekday_time,
        "weekend_lunch_time": household.chef_call_weekend_lunch_time,
        "weekend_dinner_time": household.chef_call_weekend_dinner_time,
        "scripts": {
            "weekday": build_script(db, target_day, "weekday"),
            "weekend_lunch": build_script(db, target_day, "weekend_lunch"),
            "weekend_dinner": build_script(db, target_day, "weekend_dinner"),
        },
    }


@router.post("/api/chef-calls/schedule", response_model=ChefCallOut)
def schedule(menu_date: date | None = None, db: Session = Depends(get_db)):
    call = schedule_call_for_date(db, menu_date or today())
    if call is None:
        raise HTTPException(400, "Chef calling is disabled or no cook is registered.")
    return call


@router.post("/api/chef-calls/test-call")
def test_call(call_type: str = "weekday", phone: str = "", db: Session = Depends(get_db)):
    cook = get_cook(db)
    target_phone = phone.strip() or (cook.phone if cook else "")
    if not target_phone:
        raise HTTPException(400, "No phone number provided and no cook is registered.")
    script = build_script(db, today(), call_type)
    res = place_call(target_phone, script)
    return {
        "ok": res.placed or res.status == "simulated",
        "status": res.status,
        "detail": res.detail,
        "provider_id": res.provider_id,
        "script": script,
        "phone": target_phone,
    }


@router.post("/api/chef-calls/{call_id}/run", response_model=ChefCallOut)
def run_call(call_id: int, db: Session = Depends(get_db)):
    call = db.get(ChefCall, call_id)
    if call is None:
        raise HTTPException(404, "Call not found")
    return execute_call(db, call)


@router.post("/webhooks/exotel")
async def exotel_webhook(request: Request, db: Session = Depends(get_db)):
    form = dict(await request.form())
    query = dict(request.query_params)
    data = {**query, **form}
    sid = str(data.get("CallSid") or data.get("Sid") or data.get("call_sid") or "")
    status = str(data.get("Status") or data.get("CallStatus") or data.get("status") or "")
    digits = str(data.get("Digits") or data.get("digits") or "")
    if not sid:
        return {"ok": False, "detail": "No CallSid"}
    updated = mark_from_webhook(db, sid, status, digits)
    return {"ok": True, "updated": updated.id if updated else None, "status": updated.status if updated else None}
