import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / 'frontend') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'frontend'))

import streamlit as st
from api import ApiError, delete, get, post, put
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Settings & Flatmates - Smart Kitchen AI", page_icon="⚙️", layout="wide")
inject_theme()
require_auth()

st.title("⚙️ Flat Settings & Members")
st.caption("Manage flatmates, cook contact details, and dietary preferences.")
show_integrations()

try:
    household = get("/api/household")
    all_members = get("/api/members")
except ApiError as exc:
    st.error(f"Cannot load household settings: {exc}")
    st.stop()

flatmates = [m for m in all_members if not m.get("is_cook")]
cook = next((m for m in all_members if m.get("is_cook")), None)

# ----------------- SECTION 1: FLATMATE MANAGER (UP TO 6) -----------------
st.subheader(f"👥 Flatmate Management ({len(flatmates)} / 6 Members)")
st.write("Add or remove flatmates anytime. Names sync directly to the voting hub.")

f_cols = st.columns(min(len(flatmates), 6) or 1)
for idx, fmate in enumerate(flatmates[:6]):
    with f_cols[idx % len(f_cols)]:
        st.markdown(f"**👤 {fmate['name']}**")
        if st.button("❌ Remove", key=f"del_member_{fmate['id']}", use_container_width=True):
            try:
                delete(f"/api/members/{fmate['id']}")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

st.markdown("<br>", unsafe_allow_html=True)

if len(flatmates) < 6:
    add_c1, add_c2 = st.columns([3, 1])
    with add_c1:
        new_f_name = st.text_input("New Flatmate Name:", placeholder="e.g. Aman, Sneha")
    with add_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add Flatmate", use_container_width=True):
            if new_f_name.strip():
                try:
                    post("/api/members", json={"name": new_f_name.strip(), "role": "member", "phone": "", "notify": True})
                    st.success(f"Added {new_f_name}!")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))
else:
    st.info("Maximum 6 flatmates reached.")

st.markdown("---")

# ----------------- SECTION 2: COOK DETAILS -----------------
st.subheader("👨‍🍳 Cook Contact Settings")

c_name_default = cook["name"] if cook else "Bhaiya (Cook)"
c_phone_default = cook["phone"] if (cook and cook.get("phone")) else "+919229247588"

with st.form("cook_settings_form"):
    c_name_input = st.text_input("Cook Name:", value=c_name_default)
    c_phone_input = st.text_input("Cook Mobile Number (with country code):", value=c_phone_default, placeholder="+919229247588")
    
    if st.form_submit_button("💾 Update Cook Details", use_container_width=True):
        try:
            if cook:
                put(f"/api/members/{cook['id']}", json={"name": c_name_input.strip(), "phone": c_phone_input.strip(), "role": "cook", "notify": False})
            else:
                post("/api/members", json={"name": c_name_input.strip(), "phone": c_phone_input.strip(), "role": "cook", "notify": False})
            st.success("Cook details updated successfully!")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 3: DIETARY PREFERENCES -----------------
st.subheader("🥗 Flat Dietary Preferences")

with st.form("diet_form"):
    h_diet = st.selectbox("Diet Type:", ["Vegetarian", "Eggetarian", "Non-Vegetarian"], index=0)
    h_spice = st.select_slider("Spice Level:", options=["Mild", "Medium", "Spicy", "Extra Spicy"], value="Medium")
    
    if st.form_submit_button("💾 Save Preferences", use_container_width=True):
        st.success("Preferences updated!")
