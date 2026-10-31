import streamlit as st

from api import ApiError, get, post
from ui import inject_theme, show_integrations

st.set_page_config(page_title="Automation", page_icon="⏰", layout="wide")
inject_theme()
st.title("Automation")
show_integrations()

try:
    data = get("/api/automation")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

st.metric("Timezone", data["timezone"])
st.metric("Scheduler", "Running" if data["scheduler_running"] else "Stopped")
st.write("Jobs keep running with the backend process even if this dashboard is closed. Keep `python run.py` (or the API server) running on this computer, or host it on a always-on machine.")

st.subheader("Scheduled jobs")
st.dataframe(data["jobs"], use_container_width=True)

st.subheader("Run now")
cols = st.columns(3)
labels = [("weekly_menu", "Generate weekly menu"), ("grocery_reminders", "Grocery reminders"), ("chef_calls", "Chef calls")]
for col, (name, label) in zip(cols, labels):
    with col:
        if st.button(label):
            try:
                result = post(f"/api/automation/run/{name}")
                st.success(result["result"])
            except ApiError as exc:
                st.error(str(exc))

st.subheader("Job history")
st.caption("Duplicate weekly generation for the same Monday is blocked. WhatsApp uses per-person per-date keys so reminders are not sent twice.")
st.dataframe(data["recent_runs"], use_container_width=True)
