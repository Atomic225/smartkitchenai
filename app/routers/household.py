from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import HouseholdOut, HouseholdUpdate, MemberIn, MemberOut
from app.services.household import add_member, delete_member, get_household, list_members, update_household, update_member

router = APIRouter(prefix="/api", tags=["household"])


@router.get("/household", response_model=HouseholdOut)
def read_household(db: Session = Depends(get_db)):
    return get_household(db)


@router.put("/household", response_model=HouseholdOut)
def put_household(payload: HouseholdUpdate, db: Session = Depends(get_db)):
    try:
        return update_household(db, payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/members", response_model=list[MemberOut])
def members(db: Session = Depends(get_db)):
    return list_members(db)


@router.post("/members", response_model=MemberOut)
def create_member(payload: MemberIn, db: Session = Depends(get_db)):
    return add_member(db, payload)


@router.put("/members/{member_id}", response_model=MemberOut)
def put_member(member_id: int, payload: MemberIn, db: Session = Depends(get_db)):
    try:
        return update_member(db, member_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "Member not found") from exc


@router.delete("/members/{member_id}")
def remove_member(member_id: int, db: Session = Depends(get_db)):
    try:
        delete_member(db, member_id)
    except KeyError as exc:
        raise HTTPException(404, "Member not found") from exc
    return {"ok": True}
