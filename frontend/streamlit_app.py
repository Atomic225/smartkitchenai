import streamlit as st

from api import ApiError, get, post
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Smart Kitchen AI", page_icon="🍲", layout="wide")
inject_theme()
require_auth()

st.title("Smart Kitchen AI")
st.caption("Household kitchen manager — English and Hinglish. Asia/Kolkata automation.")
show_integrations()

left, right = st.columns([1.4, 1])
with right:
    st.subheader("Today at a glance")
    try:
        cal = get("/api/calendar")
        household = get("/api/household")
        automation = get("/api/automation")
        st.metric("Household size", household["size"])
        st.metric("Reminder days", household["grocery_reminder_days"])
        st.metric("Scheduler", "Running" if automation["scheduler_running"] else "Stopped")
        st.write(f"Week {cal['week_start']} → {cal['week_end']}")
        if not cal["has_menu"]:
            if st.button("Generate this week's menu"):
                post("/api/menus/generate")
                st.rerun()
        else:
            st.success("A weekly menu is saved in the database.")
    except ApiError as exc:
        st.error(str(exc))

with left:
    st.subheader("Kitchen assistant")
    st.write("Try: `is hafte ka menu banao` · `Monday lunch ko rajma rakh do` · `Friday dinner hatao` · `aaj ka menu dikhao`")
    if "chat" not in st.session_state:
        try:
            st.session_state.chat = get("/api/chat/history")
        except ApiError:
            st.session_state.chat = []
    for message in st.session_state.chat:
        with st.chat_message(message["role"] if message["role"] in {"user", "assistant"} else "assistant"):
            st.write(message["content"])
    prompt = st.chat_input("Boliyen, English ya Hinglish...")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        try:
            result = post("/api/chat", json={"message": prompt})
            reply = result["reply"]
            if result.get("needs_clarification"):
                reply = "❓ " + reply
            if not result.get("used_openai"):
                reply += "\n\n_Offline parser used; the live AI model did not process this message._"
            st.session_state.chat.append({"role": "assistant", "content": reply})
            with st.chat_message("assistant"):
                st.write(reply)
        except ApiError as exc:
            st.error(str(exc))
