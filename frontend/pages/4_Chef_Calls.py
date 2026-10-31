import streamlit as st

from api import ApiError, get, post
from ui import inject_theme, show_integrations

st.set_page_config(page_title="Chef Calls", page_icon="📞", layout="wide")
inject_theme()
st.title("Chef calling")
show_integrations()
st.write("Calls are placed only when Exotel credentials are present. Otherwise the row is stored as `not_configured` and no phone rings.")

c1, c2 = st.columns(2)
with c1:
    if st.button("Schedule today's call"):
        try:
            post("/api/chef-calls/schedule")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
with c2:
    if st.button("Run due calls now"):
        try:
            result = post("/api/automation/run/chef_calls")
            st.info(result["result"])
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

try:
    calls = get("/api/chef-calls")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not calls:
    st.info("No chef calls yet.")
else:
    for call in calls:
        with st.expander(f"{call['menu_date']} · {call['cook_name']} · {call['status']} · attempts {call['attempts']}/{call['max_attempts']}"):
            st.write(call["script"])
            if call["error"]:
                st.warning(call["error"])
            if call["response_text"]:
                st.success(f"Cook response: {call['response_text']}")
            if call["provider_call_id"]:
                st.caption(f"Exotel CallSid: {call['provider_call_id']}")
            if st.button("Place / retry this call", key=f"run-{call['id']}"):
                updated = post(f"/api/chef-calls/{call['id']}/run")
                st.write(f"Status: {updated['status']}")
                if updated["error"]:
                    st.warning(updated["error"])
                st.rerun()
