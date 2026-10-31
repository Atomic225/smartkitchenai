from datetime import date, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import MenuItem, Recipe, WeeklyMenu
from app.schemas import MenuItemIn
from app.services.household import get_household
from app.services.timeutil import is_weekend, monday_of, week_bounds


SLOT_ORDER = ["breakfast", "brunch", "lunch", "evening_snack", "dinner"]

WEEKDAY_ROTATION = {
    "breakfast": ["Poha", "Upma", "Aloo Paratha", "Idli Sambar", "Oats and Fruit"],
    "lunch": ["Dal Tadka with Rice", "Rajma Chawal", "Mixed Vegetable Sabzi", "Palak Paneer", "Khichdi"],
    "dinner": ["Paneer Butter Masala", "Egg Curry", "Chicken Curry", "Mixed Vegetable Sabzi", "Dal Tadka with Rice"],
}

WEEKEND_ROTATION = {
    "breakfast": ["Masala Dosa", "Aloo Paratha"],
    "lunch": ["Chole Bhature", "Veg Biryani"],
    "evening_snack": ["Samosa and Chai", "Pakora"],
    "dinner": ["Pasta Arrabbiata", "Veg Pulao"],
}


def _recipe_map(db: Session) -> dict[str, Recipe]:
    return {r.name.lower(): r for r in db.query(Recipe).all()}


def _pick(recipes: dict[str, Recipe], names: list[str], index: int) -> Recipe | None:
    if not names:
        return None
    return recipes.get(names[index % len(names)].lower())


def dish_name(item: MenuItem) -> str:
    if item.custom_name:
        return item.custom_name
    if item.recipe is not None:
        return item.recipe.name
    return "Unassigned"


def serialize_item(item: MenuItem) -> dict:
    return {
        "id": item.id,
        "weekly_menu_id": item.weekly_menu_id,
        "meal_date": item.meal_date,
        "meal_slot": item.meal_slot,
        "recipe_id": item.recipe_id,
        "recipe_name": item.recipe.name if item.recipe else "",
        "custom_name": item.custom_name,
        "dish_name": dish_name(item),
        "notes": item.notes,
        "servings": item.servings,
    }


def get_week(db: Session, week_start: date | None = None) -> WeeklyMenu | None:
    start = monday_of(week_start) if week_start else None
    if start is None:
        return (
            db.query(WeeklyMenu)
            .options(joinedload(WeeklyMenu.items).joinedload(MenuItem.recipe))
            .order_by(WeeklyMenu.week_start.desc())
            .first()
        )
    return (
        db.query(WeeklyMenu)
        .options(joinedload(WeeklyMenu.items).joinedload(MenuItem.recipe))
        .filter(WeeklyMenu.week_start == start)
        .first()
    )


def list_weeks(db: Session) -> list[WeeklyMenu]:
    return (
        db.query(WeeklyMenu)
        .options(joinedload(WeeklyMenu.items).joinedload(MenuItem.recipe))
        .order_by(WeeklyMenu.week_start.desc())
        .all()
    )


def generate_weekly_menu(db: Session, week_start: date | None = None, source: str = "auto") -> WeeklyMenu:
    household = get_household(db)
    start, end = week_bounds(week_start)
    existing = db.query(WeeklyMenu).filter(WeeklyMenu.week_start == start).first()
    if existing:
        db.query(MenuItem).filter(MenuItem.weekly_menu_id == existing.id).delete()
        menu = existing
        menu.week_end = end
        menu.source = source
        menu.status = "published"
    else:
        menu = WeeklyMenu(week_start=start, week_end=end, status="published", source=source)
        db.add(menu)
        db.flush()

    recipes = _recipe_map(db)
    weekday_i = {"breakfast": 0, "lunch": 0, "dinner": 0}
    weekend_i = {"breakfast": 0, "lunch": 0, "evening_snack": 0, "dinner": 0}

    day = start
    while day <= end:
        slots = household.weekend_meals if is_weekend(day) else household.weekday_meals
        rotation = WEEKEND_ROTATION if is_weekend(day) else WEEKDAY_ROTATION
        counters = weekend_i if is_weekend(day) else weekday_i
        for slot in slots:
            names = rotation.get(slot, [])
            recipe = _pick(recipes, names, counters.get(slot, 0))
            if slot in counters:
                counters[slot] += 1
            db.add(
                MenuItem(
                    weekly_menu_id=menu.id,
                    meal_date=day,
                    meal_slot=slot,
                    recipe_id=recipe.id if recipe else None,
                    custom_name="" if recipe else f"{slot.replace('_', ' ').title()} (to assign)",
                    servings=household.size,
                )
            )
        day += timedelta(days=1)

    db.commit()
    return get_week(db, start)


def ensure_week(db: Session, week_start: date) -> WeeklyMenu:
    menu = get_week(db, week_start)
    if menu:
        return menu
    start, end = week_bounds(week_start)
    menu = WeeklyMenu(week_start=start, week_end=end, status="draft", source="manual")
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


def find_recipe(db: Session, name: str) -> Recipe | None:
    cleaned = name.strip().lower()
    if not cleaned:
        return None
    recipes = db.query(Recipe).all()
    for recipe in recipes:
        if recipe.name.lower() == cleaned or recipe.name_hi.lower() == cleaned:
            return recipe
    for recipe in recipes:
        if cleaned in recipe.name.lower() or (recipe.name_hi and cleaned in recipe.name_hi.lower()):
            return recipe
    return None


def upsert_meal(db: Session, payload: MenuItemIn) -> MenuItem:
    household = get_household(db)
    week = ensure_week(db, payload.meal_date)
    item = (
        db.query(MenuItem)
        .filter(
            MenuItem.weekly_menu_id == week.id,
            MenuItem.meal_date == payload.meal_date,
            MenuItem.meal_slot == payload.meal_slot,
        )
        .first()
    )
    servings = payload.servings or household.size
    if item is None:
        item = MenuItem(
            weekly_menu_id=week.id,
            meal_date=payload.meal_date,
            meal_slot=payload.meal_slot,
            recipe_id=payload.recipe_id,
            custom_name=payload.custom_name,
            notes=payload.notes,
            servings=servings,
        )
        db.add(item)
    else:
        item.recipe_id = payload.recipe_id
        item.custom_name = payload.custom_name
        item.notes = payload.notes
        item.servings = servings
    db.commit()
    db.refresh(item)
    if item.recipe_id:
        item.recipe = db.get(Recipe, item.recipe_id)
    return item


def delete_meal(db: Session, meal_date: date, meal_slot: str) -> bool:
    week = get_week(db, meal_date)
    if week is None:
        return False
    item = (
        db.query(MenuItem)
        .filter(
            MenuItem.weekly_menu_id == week.id,
            MenuItem.meal_date == meal_date,
            MenuItem.meal_slot == meal_slot,
        )
        .first()
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def delete_week(db: Session, week_start: date) -> bool:
    menu = db.query(WeeklyMenu).filter(WeeklyMenu.week_start == monday_of(week_start)).first()
    if menu is None:
        return False
    db.delete(menu)
    db.commit()
    return True


def meals_for_date(db: Session, day: date) -> list[MenuItem]:
    week = get_week(db, day)
    if week is None:
        return []
    return sorted(
        [item for item in week.items if item.meal_date == day],
        key=lambda item: SLOT_ORDER.index(item.meal_slot) if item.meal_slot in SLOT_ORDER else 99,
    )
