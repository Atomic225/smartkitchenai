from sqlalchemy.orm import Session

from app.models import Household, Member
from app.schemas import HouseholdUpdate, MemberIn


def get_household(db: Session) -> Household:
    household = db.query(Household).order_by(Household.id.asc()).first()
    if household is None:
        household = Household()
        db.add(household)
        db.commit()
        db.refresh(household)
    return household


def update_household(db: Session, payload: HouseholdUpdate) -> Household:
    household = get_household(db)
    data = payload.model_dump(exclude_unset=True)
    if "grocery_reminder_days" in data and data["grocery_reminder_days"] not in (2, 3):
        raise ValueError("grocery_reminder_days must be 2 or 3")
    for key, value in data.items():
        setattr(household, key, value)
    db.commit()
    db.refresh(household)
    return household


def list_members(db: Session) -> list[Member]:
    return db.query(Member).order_by(Member.id.asc()).all()


def notify_members(db: Session) -> list[Member]:
    return db.query(Member).filter(Member.notify.is_(True)).all()


def get_cook(db: Session) -> Member | None:
    return db.query(Member).filter(Member.is_cook.is_(True)).order_by(Member.id.asc()).first()


def add_member(db: Session, payload: MemberIn) -> Member:
    household = get_household(db)
    member = Member(household_id=household.id, **payload.model_dump())
    db.add(member)
    db.flush()
    household.size = db.query(Member).filter(Member.household_id == household.id).count()
    db.commit()
    db.refresh(member)
    return member


def update_member(db: Session, member_id: int, payload: MemberIn) -> Member:
    member = db.get(Member, member_id)
    if member is None:
        raise KeyError(member_id)
    for key, value in payload.model_dump().items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


def delete_member(db: Session, member_id: int) -> None:
    member = db.get(Member, member_id)
    if member is None:
        raise KeyError(member_id)
    household_id = member.household_id
    db.delete(member)
    household = db.get(Household, household_id)
    if household:
        household.size = db.query(Member).filter(Member.household_id == household_id).count()
    db.commit()
