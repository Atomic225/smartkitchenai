import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / 'frontend') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'frontend'))

import streamlit as st

from api import ApiError, delete, get, post, put
from ui import inject_theme, require_auth

st.set_page_config(page_title="Household", page_icon="👨‍👩‍👧", layout="wide")
inject_theme()
require_auth()
st.title("Household")

try:
    household = get("/api/household")
    members = get("/api/members")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

with st.form("household"):
    name = st.text_input("Household name", household["name"])
    size = st.number_input("Household size (used to scale groceries)", min_value=1, value=int(household["size"]))
    weekday = st.text_input("Weekday meals (comma separated)", ", ".join(household["weekday_meals"]))
    weekend = st.text_input("Weekend meals (comma separated)", ", ".join(household["weekend_meals"]))
    reminder = st.selectbox("WhatsApp reminder days before need", [2, 3], index=0 if household["grocery_reminder_days"] == 2 else 1)
    auto_menu = st.checkbox("Auto-create weekly menu every Sunday 18:00 IST", value=household["auto_weekly_menu"])
    
    st.markdown("#### 📞 Cook Calling Settings")
    chef_enabled = st.checkbox("Enable chef calling", value=household.get("chef_call_enabled", True))
    c_w, c_sat1, c_sat2 = st.columns(3)
    with c_w:
        chef_weekday = st.text_input("Mon–Fri Call Time", household.get("chef_call_weekday_time") or household.get("chef_call_time") or "08:30")
    with c_sat1:
        chef_sat1 = st.text_input("Sat–Sun Lunch Call", household.get("chef_call_weekend_lunch_time") or "09:30")
    with c_sat2:
        chef_sat2 = st.text_input("Sat–Sun Dinner Call", household.get("chef_call_weekend_dinner_time") or "17:00")
        
    language = st.selectbox("Chef language", ["hindi", "hinglish"], index=0 if household.get("chef_language", "hindi") == "hindi" else 1)

    if st.form_submit_button("Save household"):
        put(
            "/api/household",
            json={
                "name": name,
                "size": int(size),
                "weekday_meals": [p.strip() for p in weekday.split(",") if p.strip()],
                "weekend_meals": [p.strip() for p in weekend.split(",") if p.strip()],
                "grocery_reminder_days": int(reminder),
                "auto_weekly_menu": auto_menu,
                "chef_call_enabled": chef_enabled,
                "chef_call_time": chef_weekday.strip(),
                "chef_call_weekday_time": chef_weekday.strip(),
                "chef_call_weekend_lunch_time": chef_sat1.strip(),
                "chef_call_weekend_dinner_time": chef_sat2.strip(),
                "chef_language": language,
            },
        )
        st.success("Saved")
        st.rerun()

st.subheader("Members")
for member in members:
    with st.expander(f"{member['name']} · {member['role']}" + (" · 👨‍🍳 Cook" if member["is_cook"] else "")):
        with st.form(f"m-{member['id']}"):
            n = st.text_input("Name", member["name"])
            role = st.selectbox("Role", ["admin", "member", "cook"], index=["admin", "member", "cook"].index(member["role"]) if member["role"] in ["admin", "member", "cook"] else 1)
            phone = st.text_input("Phone", member["phone"])
            wa = st.text_input("WhatsApp number (country code, no +)", member["whatsapp_phone"])
            notify = st.checkbox("Send grocery WhatsApp", value=member["notify"])
            is_cook = st.checkbox("This person is the cook (receives voice calls)", value=member["is_cook"])
            c1, c2 = st.columns(2)
            if c1.form_submit_button("Update"):
                put(
                    f"/api/members/{member['id']}",
                    json={"name": n, "role": role, "phone": phone, "whatsapp_phone": wa, "notify": notify, "is_cook": is_cook},
                )
                st.rerun()
            if c2.form_submit_button("Delete"):
                delete(f"/api/members/{member['id']}")
                st.rerun()

st.subheader("Add member")
with st.form("add"):
    n = st.text_input("Name")
    phone = st.text_input("Phone / WhatsApp (e.g. +919876543210)")
    notify = st.checkbox("Notify on grocery list", value=True)
    is_cook = st.checkbox("Cook")
    if st.form_submit_button("Add") and n.strip():
        post(
            "/api/members",
            json={
                "name": n,
                "phone": phone,
                "whatsapp_phone": phone,
                "notify": notify,
                "is_cook": is_cook,
                "role": "cook" if is_cook else "member",
            },
        )
        st.rerun()
