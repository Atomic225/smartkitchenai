import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "frontend") not in sys.path:
    sys.path.insert(0, str(_ROOT / "frontend"))

import streamlit as st
from api import ApiError, get, post
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Flat WhatsApp Group Bot", page_icon="💬", layout="wide")
inject_theme()
require_auth()

st.title("💬 Flat WhatsApp Group Simulator")
st.caption("Interactive 6:00 PM meal decision, unlimited voting changes, and grocery confirmation state machine.")
show_integrations()

try:
    session_data = get("/api/flat-chat/session/today")
except ApiError as exc:
    st.error(f"Cannot load group chat session: {exc}")
    st.stop()

# ----------------- SECTION 1: ACTIVE SESSION STATUS -----------------
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.metric("Target Date", session_data["target_date"])
with col2:
    st.metric("Meal to Decide", session_data["meal_slot"].upper())
with col3:
    status_label = {
        "choosing_meal": "🕒 Choosing Meal (Active)",
        "waiting_grocery": "🛒 Meal Picked (Waiting Grocery)",
        "confirming_order": "⚠️ Awaiting Lock Confirmation",
        "locked": "🔒 Locked & Cook Scheduled",
    }.get(session_data["stage"], session_data["stage"])
    st.metric("Current Stage", status_label)

st.markdown("---")

# ----------------- SECTION 2: LIVE PREVIEWS -----------------
tab_kickoff, tab_reminder = st.tabs(["📢 6:00 PM Kickoff Message", "🔔 Hourly Nudge (7 PM - 1 AM)"])

with tab_kickoff:
    st.markdown("#### Message sent automatically at 6:00 PM IST (English):")
    st.info(session_data["kickoff_text"])

with tab_reminder:
    st.markdown("#### Hourly Reminder Message (English):")
    if session_data["reminder_text"]:
        st.warning(session_data["reminder_text"])
    else:
        st.success("Decision is locked! No more reminders will be sent.")

st.markdown("---")

# ----------------- SECTION 3: INTERACTIVE GROUP CHAT SIMULATOR -----------------
st.subheader("📱 Test Flatmate Replies (Simulate Group Chat)")
st.caption("Try typing like a flatmate: `Option 2`, `Paneer Butter Masala`, `Ordered`, or `Yes, lock it`.")

if "group_chat_history" not in st.session_state:
    st.session_state["group_chat_history"] = [
        {"sender": "AI Bot", "text": session_data["kickoff_text"]}
    ]

# Display chat messages
for msg in st.session_state["group_chat_history"]:
    role = "assistant" if msg["sender"] == "AI Bot" else "user"
    with st.chat_message(role):
        st.markdown(f"**{msg['sender']}:**\n{msg['text']}")

user_input = st.chat_input("Reply as flatmate (e.g. Option 1, Change to Rajma, Ordered, Yes)...")
if user_input:
    current_user = st.session_state.get("active_user", "Flatmate")
    st.session_state["group_chat_history"].append({"sender": current_user, "text": user_input})
    try:
        res = post("/api/flat-chat/message", json={"text": user_input, "sender": current_user})
        bot_reply = res.get("reply", "")
        if bot_reply:
            st.session_state["group_chat_history"].append({"sender": "AI Bot", "text": bot_reply})
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))
