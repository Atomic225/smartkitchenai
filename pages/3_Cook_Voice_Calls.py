import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / 'frontend') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'frontend'))

import streamlit as st
from api import ApiError, get, post, put
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Cook Calls & Logs - Smart Kitchen AI", page_icon="📞", layout="wide")
inject_theme()
require_auth()

st.title("📞 Cook Voice Calling & Logs")
st.caption("Automated & on-demand natural Hindi phone calls to your cook powered by Twilio Voice and Amazon Polly Aditi.")
show_integrations()

try:
    household = get("/api/household")
    preview_data = get("/api/chef-calls/preview")
    members = get("/api/members")
    calls = get("/api/chef-calls")
except ApiError as exc:
    st.error(f"Cannot load calling details: {exc}")
    st.stop()

cook = next((m for m in members if m.get("is_cook")), None)
cook_name = cook["name"] if cook else "Bhaiya (Cook)"
cook_phone = cook["phone"] if (cook and cook.get("phone")) else "+919229247588"

# ----------------- SECTION 1: COOK PROFILE & TIMINGS -----------------
col_c1, col_c2 = st.columns([1, 1.4])

with col_c1:
    st.subheader("👨‍🍳 Cook Details")
    st.success(f"**Name:** {cook_name}  \n**Phone:** `{cook_phone}`")
    st.info("🎙️ **Voice Engine:** Spoken Hindi (`hi-IN`) via `Polly.Aditi`.")

with col_c2:
    st.subheader("⏰ Automated Call Schedule")
    with st.form("call_schedule_form"):
        c_enabled = st.checkbox("Enable Automated Scheduled Calling", value=bool(household.get("chef_call_enabled", True)))
        c_weekday = st.text_input("Mon–Fri Daily Call Time (24h IST):", value=household.get("chef_call_weekday_time") or "08:30")
        
        c1, c2 = st.columns(2)
        with c1:
            c_sat_l = st.text_input("Sat–Sun Lunch Call:", value=household.get("chef_call_weekend_lunch_time") or "09:30")
        with c2:
            c_sat_d = st.text_input("Sat–Sun Dinner Call:", value=household.get("chef_call_weekend_dinner_time") or "17:00")
            
        if st.form_submit_button("💾 Save Timings", use_container_width=True):
            try:
                put("/api/household", json={
                    "chef_call_enabled": c_enabled,
                    "chef_call_weekday_time": c_weekday.strip(),
                    "chef_call_weekend_lunch_time": c_sat_l.strip(),
                    "chef_call_weekend_dinner_time": c_sat_d.strip(),
                    "chef_call_time": c_weekday.strip(),
                    "chef_language": "hindi",
                })
                st.success("Timings saved successfully!")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 2: INSTANT CALL WITH EDITABLE SCRIPT -----------------
st.subheader("🚀 Place Instant Voice Call")

script_col1, script_col2 = st.columns([1.6, 1])

with script_col1:
    default_script = preview_data.get("scripts", {}).get("weekday", "Namaste bhaiya, kal ka kitchen menu tayar hai.")
    edited_text = st.text_area(
        "Spoken Hindi Script (100% Editable):",
        value=default_script,
        height=110,
        help="Type or edit the exact Hindi sentences the cook will hear.",
    )

with script_col2:
    target_p = st.text_input("Destination Mobile Number:", value=cook_phone)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📞 Ring Cook's Phone Now", type="primary", use_container_width=True):
        if not target_p.strip():
            st.error("Please enter a phone number.")
        else:
            with st.spinner("Dialing cook via Twilio Voice..."):
                try:
                    res = post("/api/flat-chat/call-cook", json={"script": edited_text.strip(), "phone": target_p.strip()})
                    if res.get("ok"):
                        st.success(f"🎉 Call Placed! Status: **{res.get('status').upper()}**")
                        if res.get("provider_id"):
                            st.caption(f"Twilio Call SID: `{res.get('provider_id')}`")
                    else:
                        detail = res.get("detail", "")
                        if "573002" in detail or "verified recipient" in detail.lower():
                            st.error(
                                f"⚠️ **Twilio Trial Account Restriction:**\n\n"
                                f"The number `{target_p}` must be verified once in Twilio Console before calling.\n\n"
                                f"👉 **[Click here to verify in Twilio Console](https://console.twilio.com/us1/develop/phone-numbers/manage/verified-caller-ids)**"
                            )
                        else:
                            st.warning(f"Status: {res.get('status')} — {detail}")
                except ApiError as exc:
                    st.error(f"Call failed: {exc}")

st.markdown("---")

# ----------------- SECTION 3: CALL LOGS & HISTORY TABLE -----------------
st.subheader("📋 Recent Call Logs & History")

if calls:
    table_data = []
    for c in calls[:10]:
        table_data.append({
            "Scheduled Time": c.get("scheduled_time", "N/A"),
            "Status": c.get("status", "unknown").upper(),
            "Twilio Call SID": c.get("provider_call_id") or "N/A",
            "Attempts": c.get("attempts", 1),
            "Language": "Hindi (Polly.Aditi)",
        })
    st.dataframe(table_data, use_container_width=True)
else:
    st.info("No calls placed yet. Click 'Ring Cook's Phone Now' above to test.")
