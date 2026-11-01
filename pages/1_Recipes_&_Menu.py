import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / 'frontend') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'frontend'))

import streamlit as st
from api import ApiError, get, post
from ui import inject_theme, require_auth

st.set_page_config(page_title="Recipes & Menu - Smart Kitchen AI", page_icon="🍲", layout="wide")
inject_theme()
require_auth()

st.title("🍲 Recipes & Menu Catalog")
st.caption("Browse kitchen recipes, search by ingredients, or propose dishes for tonight's flat vote.")

try:
    recipes = get("/api/recipes")
except ApiError as exc:
    st.error(f"Cannot load recipes: {exc}")
    st.stop()

# ----------------- SEARCH & FILTERS -----------------
f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
with f_col1:
    search_q = st.text_input("🔍 Search by dish name or ingredient:", placeholder="e.g. Paneer, Paratha, Aloo, Dal...")
with f_col2:
    cuisine_filter = st.selectbox("Cuisine / Category:", ["All", "Breakfast", "Lunch", "Dinner", "Quick Veg"])
with f_col3:
    st.metric("Total Recipes", len(recipes))

# Filter recipes
filtered = recipes
if search_q.strip():
    q = search_q.strip().lower()
    filtered = [
        r for r in filtered
        if q in r["name"].lower()
        or q in (r.get("name_hi") or "").lower()
        or any(q in ing.get("name", "").lower() for ing in (r.get("ingredients") or []))
    ]

if cuisine_filter != "All":
    cf = cuisine_filter.lower()
    filtered = [
        r for r in filtered
        if cf in [m.lower() for m in r.get("meal_types", [])]
        or cf in [t.lower() for t in r.get("tags", [])]
    ]

st.markdown("---")

# ----------------- RECIPES GRID -----------------
st.subheader(f"📖 Available Dishes ({len(filtered)})")

dish_icons = {"Poha": "🍲", "Upma": "🥣", "Aloo Paratha": "🥞", "Idli Sambar": "🥟", "Paneer": "🥘", "Dal": "🍛", "Biryani": "🍚"}

for r in filtered:
    icon = next((v for k, v in dish_icons.items() if k.lower() in r["name"].lower()), "🍽️")
    hi_name = f" ({r['name_hi']})" if r.get("name_hi") else ""
    
    with st.expander(f"{icon} **{r['name']}**{hi_name} • {', '.join(r.get('meal_types', []))}"):
        col_r1, col_r2, col_r3 = st.columns([1.5, 1.5, 1])
        
        with col_r1:
            st.markdown("##### 🛒 Ingredients")
            ings = r.get("ingredients") or []
            if ings:
                for ing in ings:
                    st.write(f"- {ing.get('name', '').capitalize()} — `{ing.get('qty', '')} {ing.get('unit', '')}`")
            else:
                st.caption("Pantry basics required.")
                
        with col_r2:
            st.markdown("##### 👨‍🍳 Cook Hindi Instructions")
            st.info(r.get("hindi_script") or "Kitchen instructions available on calling.")
            if r.get("instructions"):
                st.caption(f"**English:** {r['instructions']}")
                
        with col_r3:
            st.markdown("##### 🌟 Quick Actions")
            if st.button(f"🗳️ Vote for {r['name']}", key=f"vote_cat_{r['id']}", use_container_width=True):
                try:
                    post("/api/flat-chat/vote", json={"dish_name": r["name"], "voter": "Flatmate"})
                    st.success(f"Set **{r['name']}** as the flat's choice!")
                except ApiError as exc:
                    st.error(str(exc))
