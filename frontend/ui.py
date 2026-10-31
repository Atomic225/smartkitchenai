import streamlit as st

from api import ApiError, get


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
                f"<span class='status-pill {klass}'>{item['name']}: {item['mode']}</span>",
                unsafe_allow_html=True,
            )
            st.caption(item["detail"])
    return items
