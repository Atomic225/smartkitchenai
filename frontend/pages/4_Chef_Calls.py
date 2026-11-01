import streamlit as st

from api import ApiError, get, post, put
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Chef Calls", page_icon="📞", layout="wide")
inject_theme()
require_auth()

st.title("📞 Cook Voice Calling")
st.caption("Automated Hindi phone calls to your cook: 1 call Mon–Fri, 2 calls on Sat & Sun with customizable times.")
show_integrations()

try:
    household = get("/api/household")
    preview_data = get("/api/chef-calls/preview")
    members = get("/api/members")
    calls = get("/api/chef-calls")
except ApiError as exc:
    st.error(f"Cannot load chef calling details: {exc}")
    st.stop()

cook = next((m for m in members if m.get("is_cook")), None)

# ----------------- SECTION 1: COOK & CALL SCHEDULE SETTINGS -----------------
st.subheader("⚙️ Calling Schedule & Timings")
st.write("Configure the exact times our AI calls your cook. Timings can be changed at any time.")

col_cook, col_sched = st.columns([1, 1.3])

with col_cook:
    st.markdown("### 👨‍🍳 Cook Details")
    if cook:
        st.success(f"**Cook:** {cook['name']}  \n**Phone:** `{cook['phone'] or 'No phone added'}`")
    else:
        st.warning("⚠️ No cook marked yet. Please mark a member as Cook in the **Household** page so the system knows whose phone to call.")

    st.info("💡 **Voice Language:** Spoken Hindi (`hi-IN`) with polite greetings (*'Namaste bhaiya, aaj ka menu yeh hai...'*)")

with col_sched:
    st.markdown("### ⏰ Daily Timings (Asia/Kolkata)")
    with st.form("chef_schedule_form"):
        c_enabled = st.checkbox("Enable Automated Cook Calling", value=bool(household.get("chef_call_enabled", True)))
        
        c_weekday = st.text_input(
            "📅 Mon – Fri Call Time (1 call / day)",
            value=household.get("chef_call_weekday_time") or household.get("chef_call_time") or "08:30",
            help="HH:MM in 24-hr IST. Covers Lunch & Dinner briefing.",
        )
        
        c1, c2 = st.columns(2)
        with c1:
            c_sat_lunch = st.text_input(
                "🏖️ Sat – Sun Lunch Call",
                value=household.get("chef_call_weekend_lunch_time") or "09:30",
                help="HH:MM in 24-hr IST. Briefs lunch & afternoon meals.",
            )
        with c2:
            c_sat_dinner = st.text_input(
                "🌙 Sat – Sun Dinner Call",
                value=household.get("chef_call_weekend_dinner_time") or "17:00",
                help="HH:MM in 24-hr IST. Briefs evening & dinner meals.",
            )

        if st.form_submit_button("💾 Save Timings", use_container_width=True):
            try:
                put(
                    "/api/household",
                    json={
                        "chef_call_enabled": c_enabled,
                        "chef_call_weekday_time": c_weekday.strip(),
                        "chef_call_weekend_lunch_time": c_sat_lunch.strip(),
                        "chef_call_weekend_dinner_time": c_sat_dinner.strip(),
                        "chef_call_time": c_weekday.strip(),
                        "chef_language": "hindi",
                    },
                )
                st.success("✅ Timings updated successfully!")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 2: TODAY'S HINDI SCRIPT & TEST CALL -----------------
st.subheader("🎙️ Today's Hindi Script & Instant Test Call")

col_script, col_test = st.columns([1.3, 1])

with col_script:
    st.markdown("#### 📜 Spoken Script Preview")
    scripts = preview_data.get("scripts", {})
    is_weekend = preview_data.get("is_weekend", False)

    if is_weekend:
        st.caption("Today is a **Weekend (Saturday/Sunday)** — 2 calls scheduled.")
        tab1, tab2 = st.tabs(["🏖️ Call 1: Lunch Briefing", "🌙 Call 2: Dinner Briefing"])
        with tab1:
            st.info(scripts.get("weekend_lunch", ""))
        with tab2:
            st.info(scripts.get("weekend_dinner", ""))
    else:
        st.caption("Today is a **Weekday (Monday–Friday)** — 1 daily call scheduled.")
        st.info(scripts.get("weekday", ""))

with col_test:
    st.markdown("#### 📞 Place Instant Test Call")
    st.caption("Test the call right now without waiting for the scheduled time.")
    default_test_phone = cook["phone"] if (cook and cook["phone"]) else ""
    with st.form("test_call_form"):
        test_phone = st.text_input("Destination Mobile Number", value=default_test_phone, placeholder="+919876543210")
        call_type_choice = st.selectbox(
            "Call Type Script",
            options=["weekday", "weekend_lunch", "weekend_dinner"],
            format_func=lambda x: {
                "weekday": "📅 Mon-Fri Full Day Menu",
                "weekend_lunch": "🏖️ Weekend Call 1 (Lunch)",
                "weekend_dinner": "🌙 Weekend Call 2 (Dinner)",
            }.get(x, x),
        )
        test_submitted = st.form_submit_button("🚀 Ring Phone Now", use_container_width=True)
        if test_submitted:
            if not test_phone.strip():
                st.error("Please enter a phone number.")
            else:
                try:
                    res = post("/api/chef-calls/test-call", params={"call_type": call_type_choice, "phone": test_phone.strip()})
                    if res.get("ok"):
                        st.success(f"✅ Call {res.get('status').upper()}! {res.get('detail')}")
                    else:
                        st.warning(f"Status: {res.get('status')} - {res.get('detail')}")
                except ApiError as exc:
                    st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 3: CALL LOGS & HISTORY -----------------
st.subheader("📋 Call Logs & History")

col_act1, col_act2 = st.columns(2)
with col_act1:
    if st.button("📅 Schedule Today's Calls"):
        try:
            post("/api/chef-calls/schedule")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
with col_act2:
    if st.button("⚡ Run Due Calls Now"):
        try:
            result = post("/api/automation/run/chef_calls")
            st.info(result["result"])
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

if not calls:
    st.info("No cook calls recorded yet.")
else:
    for call in calls:
        call_type_label = {
            "weekday": "Mon-Fri Daily",
            "weekend_lunch": "Weekend Lunch (Call 1)",
            "weekend_dinner": "Weekend Dinner (Call 2)",
            "daily": "Daily",
        }.get(call.get("call_type", "daily"), call.get("call_type", "daily"))

        title = f"{call['menu_date']} · {call_type_label} · {call['cook_name']} · Status: {call['status']} (attempts {call['attempts']}/{call['max_attempts']})"
        with st.expander(title):
            st.write(f"**Hindi Script:** {call['script']}")
            if call.get("scheduled_for"):
                st.caption(f"Scheduled for: {call['scheduled_for']}")
            if call["error"]:
                st.warning(call["error"])
            if call["response_text"]:
                st.success(f"Cook response: {call['response_text']}")
            if call["provider_call_id"]:
                st.caption(f"Provider ID: {call['provider_call_id']}")
            if st.button("Place / retry this call", key=f"run-{call['id']}"):
                try:
                    updated = post(f"/api/chef-calls/{call['id']}/run")
                    st.write(f"Status: {updated['status']}")
                    if updated["error"]:
                        st.warning(updated["error"])
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))
