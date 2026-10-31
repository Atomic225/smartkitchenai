from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChefCall
from app.schemas import ChefCallOut
from app.services.chef import execute_call, list_calls, mark_from_webhook, schedule_call_for_date
from app.services.timeutil import today

router = APIRouter(tags=["chef"])


@router.get("/api/chef-calls", response_model=list[ChefCallOut])
def calls(db: Session = Depends(get_db)):
    return list_calls(db)


@router.post("/api/chef-calls/schedule", response_model=ChefCallOut)
def schedule(menu_date: date | None = None, db: Session = Depends(get_db)):
    call = schedule_call_for_date(db, menu_date or today())
    if call is None:
        raise HTTPException(400, "Chef calling is disabled or no cook is registered.")
    return call


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
