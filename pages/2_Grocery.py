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
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Grocery", page_icon="🛒", layout="wide")
inject_theme()
require_auth()
st.title("Grocery list")
show_integrations()

cols = st.columns(3)
with cols[0]:
    if st.button("Rebuild from weekly menu", type="primary"):
        try:
            post("/api/grocery/rebuild")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
with cols[1]:
    if st.button("Run WhatsApp reminders now"):
        try:
            rows = post("/api/grocery/reminders/run")
            if not rows:
                st.info("Nothing is due 2–3 days from now.")
            for row in rows:
                st.write(f"{row['recipient_name']}: **{row['status']}** — {row['error'] or 'accepted by provider'}")
        except ApiError as exc:
            st.error(str(exc))

try:
    listing = get("/api/grocery")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not listing:
    st.info("No shopping list yet. Generate a weekly menu first.")
    st.stop()

st.caption("Duplicate ingredients are combined. Quantities are scaled to household size.")
grouped: dict[str, list] = defaultdict(list)
for item in listing["items"]:
    grouped[item["category"]].append(item)

for category, items in grouped.items():
    st.subheader(category.replace("_", " ").title())
    for item in items:
        checked = st.checkbox(
            f"{item['name']} — {item['quantity']} {item['unit']} (needed by {item['needed_by']})",
            value=item["purchased"],
            key=f"g-{item['id']}",
        )
        if checked != item["purchased"]:
            post(f"/api/grocery/items/{item['id']}/purchased", params={"purchased": checked})
            st.rerun()

st.subheader("Notification log")
st.caption("Rows with status `not_configured` mean no WhatsApp message was sent.")
try:
    notes = get("/api/notifications")
    if notes:
        st.dataframe(notes, use_container_width=True)
    else:
        st.write("No notification attempts yet.")
except ApiError as exc:
    st.error(str(exc))
