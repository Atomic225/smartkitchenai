import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / 'frontend') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'frontend'))

from collections import defaultdict
import streamlit as st
from api import ApiError, get, post
from ui import inject_theme, require_auth

st.set_page_config(page_title="Smart Groceries - Smart Kitchen AI", page_icon="🛒", layout="wide")
inject_theme()
require_auth()

st.title("🛒 Smart Groceries & Pantry")
st.caption("Auto-generated ingredient shopping list scaled for your flat with 1-click quick-delivery shortcuts.")

# ----------------- QUICK DELIVERY SHORTCUTS -----------------
st.subheader("⚡ Quick Delivery Apps")
st.write("Order missing ingredients in 10 minutes:")

b_col1, b_col2, b_col3 = st.columns(3)
with b_col1:
    st.link_button("🟡 Open Blinkit", "https://blinkit.com", use_container_width=True)
with b_col2:
    st.link_button("🟣 Open Zepto", "https://www.zeptonow.com", use_container_width=True)
with b_col3:
    st.link_button("🟠 Open Swiggy Instamart", "https://www.swiggy.com/instamart", use_container_width=True)

st.markdown("---")

# ----------------- ACTIVE MEAL GROCERIES -----------------
try:
    session_data = get("/api/flat-chat/session/today")
    dish = session_data.get("selected_recipe_name", "")
    ingredients = session_data.get("selected_ingredients", [])
except ApiError:
    dish = ""
    ingredients = []

st.subheader(f"🥣 Tonight's / Tomorrow's Menu: {dish or 'No dish selected yet'}")
if dish and ingredients:
    st.caption(f"Ingredients required for **{dish}**:")
    ing_cols = st.columns(3)
    for idx, ing in enumerate(ingredients):
        with ing_cols[idx % 3]:
            st.checkbox(
                f"{ing.get('name', '').capitalize()} — `{ing.get('qty', '')} {ing.get('unit', '')}`",
                value=True,
                key=f"ing_active_{idx}",
            )
else:
    st.info("Pick a meal on the Home page to see its specific required ingredients.")

st.markdown("---")

# ----------------- PANTRY & SHOPPING LIST -----------------
st.subheader("📋 Full Household Shopping List")

try:
    listing = get("/api/grocery")
except ApiError as exc:
    listing = None

if listing and listing.get("items"):
    grouped = defaultdict(list)
    for item in listing["items"]:
        grouped[item["category"]].append(item)

    for category, items in grouped.items():
        with st.expander(f"📦 {category.replace('_', ' ').title()} ({len(items)} items)", expanded=True):
            cols = st.columns(3)
            for idx, item in enumerate(items):
                with cols[idx % 3]:
                    st.checkbox(
                        f"**{item['name'].capitalize()}** — {item['quantity']} {item['unit']}",
                        value=False,
                        key=f"item_{item['id']}",
                        help=f"Needed by {item.get('needed_by', 'this week')}",
                    )
else:
    st.info("Pantry essentials (Oil, Salt, Spices, Atta/Rice) are up to date.")
