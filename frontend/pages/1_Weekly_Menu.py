import streamlit as st

from api import ApiError, delete, get, post, put
from ui import inject_theme, require_auth

st.set_page_config(page_title="Weekly Menu", page_icon="📅", layout="wide")
inject_theme()
require_auth()
st.title("Weekly menu")

try:
    recipes = get("/api/recipes")
    cal = get("/api/calendar")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

recipe_names = {r["name"]: r["id"] for r in recipes}
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("Generate / regenerate this week", type="primary"):
        post("/api/menus/generate")
        st.rerun()
    st.caption(f"Week {cal['week_start']} to {cal['week_end']}. Weekdays and weekends use different meal slots.")

if not cal["has_menu"]:
    st.info("No menu saved for this week yet.")
    st.stop()

for day in cal["days"]:
    with st.expander(f"{day['weekday']} {day['date']}{' · weekend' if day['weekend'] else ''}", expanded=True):
        for meal in day["meals"]:
            slot = meal["meal_slot"]
            cols = st.columns([2, 3, 2, 1, 1])
            cols[0].write(slot.replace("_", " ").title())
            current = meal.get("dish_name") or ""
            options = ["(custom)"] + list(recipe_names.keys())
            default_index = options.index(current) if current in recipe_names else 0
            chosen = cols[1].selectbox("Dish", options, index=default_index, key=f"sel-{day['date']}-{slot}", label_visibility="collapsed")
            custom = cols[2].text_input("Custom", value="" if chosen != "(custom)" else current, key=f"cust-{day['date']}-{slot}", label_visibility="collapsed", placeholder="Custom dish")
            if cols[3].button("Save", key=f"save-{day['date']}-{slot}"):
                payload = {
                    "meal_date": day["date"],
                    "meal_slot": slot,
                    "recipe_id": recipe_names.get(chosen) if chosen != "(custom)" else None,
                    "custom_name": custom if chosen == "(custom)" else "",
                    "notes": meal.get("notes") or "",
                }
                try:
                    put("/api/menus/items", json=payload)
                    st.success("Saved")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))
            if meal.get("id") and cols[4].button("Delete", key=f"del-{day['date']}-{slot}"):
                delete("/api/menus/items", params={"meal_date": day["date"], "meal_slot": slot})
                st.rerun()
