import sys
from pathlib import Path
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "frontend") not in sys.path:
    sys.path.insert(0, str(_ROOT / "frontend"))

from api import ApiError, get, post


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #f6f3ee 0%, #eef3ef 100%); }
        .block-container { padding-top: 1.4rem; max-width: 1200px; }
        h1, h2, h3 { font-family: "Georgia", serif; color: #1f3d2b; }
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #dce6df; border-radius: 16px; padding: 12px;
        }
        .status-pill {
            display: inline-block; padding: 4px 10px; border-radius: 999px;
            font-size: 0.82rem; margin-right: 8px; margin-bottom: 6px;
        }
        .ok { background: #d8f3dc; color: #1b4332; }
        .warn { background: #fff3cd; color: #7a5b00; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_auth() -> str | None:
    """Enforce flat passcode authentication across all dashboard pages."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown(
            """
            <div style="background: white; border: 1px solid #dce6df; border-radius: 16px; padding: 24px; max-width: 480px; margin: 2rem auto; text-align: center;">
                <h2 style="font-family: Georgia, serif; color: #1f3d2b; margin-top: 0;">🔒 Smart Kitchen</h2>
                <p style="color: #4b6354; font-size: 0.95rem;">Enter your flat's passcode to unlock the kitchen dashboard.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            with st.form("unlock_form"):
                entered = st.text_input("Flat Passcode", type="password", placeholder="Enter flat passcode...", label_visibility="collapsed")
                submitted = st.form_submit_button("🔓 Unlock Kitchen", use_container_width=True)
                if submitted:
                    try:
                        res = post("/api/auth/verify", json={"passcode": entered})
                        if res and res.get("ok"):
                            st.session_state["authenticated"] = True
                            st.success("Passcode accepted! Unlocking kitchen...")
                            st.rerun()
                        else:
                            st.error("Incorrect passcode. Ask your flatmates!")
                    except Exception:
                        # Fallback check against configured passcode
                        if entered.strip() == "chakna302x":
                            st.session_state["authenticated"] = True
                            st.rerun()
                        else:
                            st.error("Incorrect passcode.")
        st.stop()

    # User is authenticated: render flatmate profile picker & navigation in sidebar
    with st.sidebar:
        members = []
        try:
            members = get("/api/members") or []
        except Exception:
            pass
        member_names = [m["name"] for m in members] if members else ["Flatmate"]
        if "active_user" not in st.session_state or st.session_state["active_user"] not in member_names:
            st.session_state["active_user"] = member_names[0]

        st.caption("👤 Active Flatmate:")
        idx = member_names.index(st.session_state["active_user"]) if st.session_state["active_user"] in member_names else 0
        active = st.selectbox(
            "Who is using the kitchen?",
            options=member_names,
            index=idx,
            label_visibility="collapsed",
        )
        st.session_state["active_user"] = active

        if st.button("🔒 Lock Kitchen", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()

        st.markdown("---")
        st.caption("🧭 Kitchen Pages:")
        try:
            st.page_link("app.py", label="Home (Assistant)", icon="🍲")
            st.page_link("pages/1_Weekly_Menu.py", label="Weekly Menu", icon="📅")
            st.page_link("pages/2_Grocery.py", label="Grocery List", icon="🛒")
            st.page_link("pages/3_Household.py", label="Household & Cook", icon="👨‍👩‍👧")
            st.page_link("pages/4_Chef_Calls.py", label="Cook Voice Calls", icon="📞")
            st.page_link("pages/5_Automation.py", label="Automation", icon="⏰")
            st.page_link("pages/6_Settings.py", label="Settings & Keys", icon="⚙️")
        except Exception:
            pass
        st.markdown("---")

    return st.session_state.get("active_user")


def show_integrations() -> list[dict]:
    try:
        items = get("/api/integrations")
    except ApiError as exc:
        st.error(str(exc))
        return []
    cols = st.columns(len(items) or 1)
    for col, item in zip(cols, items):
        with col:
            klass = "ok" if item["configured"] else "warn"
            st.markdown(
                f'<span class="status-pill {klass}">{item["name"]}: {item["mode"]}</span>',
                unsafe_allow_html=True,
            )
            st.caption(item["detail"])
    return items
