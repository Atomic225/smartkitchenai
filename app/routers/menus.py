from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe
from app.schemas import MenuItemIn, MenuItemOut, RecipeOut, WeeklyMenuOut
from app.services.grocery import build_shopping_list
from app.services.menu import (
    delete_meal,
    generate_weekly_menu,
    get_week,
    list_weeks,
    serialize_item,
    upsert_meal,
)
from app.services.timeutil import monday_of, today, week_bounds

router = APIRouter(prefix="/api", tags=["menus"])


def _menu_out(menu) -> WeeklyMenuOut:
    items = [MenuItemOut(**serialize_item(item)) for item in sorted(menu.items, key=lambda i: (i.meal_date, i.meal_slot))]
    return WeeklyMenuOut(
        id=menu.id,
        week_start=menu.week_start,
        week_end=menu.week_end,
        status=menu.status,
        source=menu.source,
        notes=menu.notes,
        items=items,
    )


@router.get("/recipes", response_model=list[RecipeOut])
def recipes(db: Session = Depends(get_db)) -> list[Recipe]:
    return db.query(Recipe).order_by(Recipe.name.asc()).all()


@router.get("/menus", response_model=list[WeeklyMenuOut])
def menus(db: Session = Depends(get_db)) -> list[WeeklyMenuOut]:
    return [_menu_out(menu) for menu in list_weeks(db)]


@router.get("/menus/current", response_model=WeeklyMenuOut)
def current_menu(week_start: date | None = None, db: Session = Depends(get_db)) -> WeeklyMenuOut:
    start = monday_of(week_start or today())
    menu = get_week(db, start)
    if menu is None:
        raise HTTPException(404, "No menu for that week. Generate one first.")
    return _menu_out(menu)


@router.post("/menus/generate", response_model=WeeklyMenuOut)
def generate(week_start: date | None = None, db: Session = Depends(get_db)) -> WeeklyMenuOut:
    start = monday_of(week_start or today())
    menu = generate_weekly_menu(db, start, source="manual")
    try:
        build_shopping_list(db, menu.week_start)
    except ValueError:
        pass
    return _menu_out(menu)


@router.put("/menus/items", response_model=MenuItemOut)
def put_item(payload: MenuItemIn, db: Session = Depends(get_db)) -> MenuItemOut:
    item = upsert_meal(db, payload)
    week = get_week(db, payload.meal_date)
    if week:
        try:
            build_shopping_list(db, week.week_start)
        except ValueError:
            pass
    return MenuItemOut(**serialize_item(item))


@router.delete("/menus/items")
def remove_item(meal_date: date, meal_slot: str, db: Session = Depends(get_db)) -> dict:
    if not delete_meal(db, meal_date, meal_slot):
        raise HTTPException(404, "Meal not found")
    return {"ok": True}


@router.get("/calendar")
def calendar(week_start: date | None = None, db: Session = Depends(get_db)) -> dict:
    start, end = week_bounds(week_start or today())
    menu = get_week(db, start)
    days = []
    from datetime import timedelta

    from app.services.household import get_household
    from app.services.timeutil import is_weekend

    household = get_household(db)
    cursor = start
    while cursor <= end:
        slots = household.weekend_meals if is_weekend(cursor) else household.weekday_meals
        slot_meals = []
        if menu:
            by_slot = {item.meal_slot: item for item in menu.items if item.meal_date == cursor}
        else:
            by_slot = {}
        for slot in slots:
            item = by_slot.get(slot)
            slot_meals.append(serialize_item(item) if item else {"meal_date": cursor.isoformat(), "meal_slot": slot, "dish_name": ""})
        days.append({"date": cursor.isoformat(), "weekday": cursor.strftime("%A"), "weekend": is_weekend(cursor), "meals": slot_meals})
        cursor += timedelta(days=1)
    return {"week_start": start.isoformat(), "week_end": end.isoformat(), "has_menu": menu is not None, "days": days}
