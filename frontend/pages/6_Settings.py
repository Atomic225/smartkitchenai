import streamlit as st

from api import ApiError, get, post
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
inject_theme()
require_auth()
st.title("Settings and credentials")
show_integrations()

st.markdown(
    """
### Accounts you need

1. **Google Gemini** — API key from [aistudio.google.com](https://aistudio.google.com/app/apikey).
   Free tier available. Powers natural English/Hinglish chat with tool-calling.
2. **WhatsApp Business Cloud API** (Meta) — a WhatsApp Business app, permanent or temporary access token, and Phone Number ID.
3. **Exotel** — account SID, API key, API token, a virtual ExoPhone (Caller ID), and preferably an applet/app ID that can speak the menu script.
4. No extra account is required for the database; it is a local SQLite file.

The app works without secrets. Unconfigured channels are logged honestly and **never** marked as sent or completed.
"""
)

try:
    env = get("/api/settings/env")
except ApiError as exc:
    st.error(str(exc))
    st.stop()

with st.form("secrets"):
    # ── Gemini (primary AI provider) ────────────────────────────────────────
    st.subheader("🤖 Google Gemini AI  *(primary AI provider)*")
    gemini_key = st.text_input(
        "GEMINI_API_KEY",
        type="password",
        placeholder="AIza... (leave blank to keep existing key)",
        help="Get a free key at https://aistudio.google.com/app/apikey",
    )
    gemini_model = st.text_input(
        "GEMINI_MODEL",
        value=env.get("gemini_model") or "gemini-3.5-flash-lite",
        help="Recommended: gemini-3.5-flash-lite. Usage limits depend on your Google AI Studio free-tier access.",
    )

    st.caption(
        "✅ Key set" if env.get("gemini_api_key_set") else
        "⚠️ Not configured — offline parser will be used until you add a key."
    )

    # ── OpenAI (legacy, optional) ────────────────────────────────────────────
    with st.expander("OpenAI (legacy — Gemini takes priority)", expanded=False):
        st.caption("Only needed if you still have a paid OpenAI key and want to keep it as a fallback.")
        openai_key = st.text_input("OPENAI_API_KEY", type="password", placeholder="sk-... (optional)")
        openai_model = st.text_input("OPENAI_MODEL", env.get("openai_model") or "gpt-4o-mini")

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    st.subheader("WhatsApp Business Cloud API")
    wa_token = st.text_input("WHATSAPP_ACCESS_TOKEN", type="password")
    wa_phone = st.text_input("WHATSAPP_PHONE_NUMBER_ID", env.get("whatsapp_phone_number_id") or "")
    wa_biz = st.text_input("WHATSAPP_BUSINESS_ACCOUNT_ID")

    # ── Exotel ───────────────────────────────────────────────────────────────
    st.subheader("Exotel (outbound voice calls to chef)")
    exo_sid = st.text_input("EXOTEL_SID", env.get("exotel_sid") or "")
    exo_key = st.text_input("EXOTEL_API_KEY", type="password")
    exo_token = st.text_input("EXOTEL_API_TOKEN", type="password")
    exo_caller = st.text_input("EXOTEL_CALLER_ID", env.get("exotel_caller_id") or "")
    exo_app = st.text_input("EXOTEL_APP_ID")
    exo_cb = st.text_input("EXOTEL_STATUS_CALLBACK_URL", placeholder="https://your-public-host/webhooks/exotel")

    
    # ── Flat Security ────────────────────────────────────────────────────────
    st.subheader("🔒 Flat Security")
    flat_code = st.text_input("FLAT_PASSCODE", value=env.get("flat_passcode") or "chakna302x", help="The shared passcode your flatmates use to unlock the kitchen.")

    if st.form_submit_button("💾 Save credentials to .env"):
        payload = {
            "GEMINI_MODEL": gemini_model,
            "FLAT_PASSCODE": flat_code.strip(),
            "OPENAI_MODEL": openai_model,
            "WHATSAPP_PHONE_NUMBER_ID": wa_phone,
            "WHATSAPP_BUSINESS_ACCOUNT_ID": wa_biz,
            "EXOTEL_SID": exo_sid,
            "EXOTEL_CALLER_ID": exo_caller,
            "EXOTEL_APP_ID": exo_app,
            "EXOTEL_STATUS_CALLBACK_URL": exo_cb,
        }
        # Only write secrets if non-blank (prevents accidental clearing)
        if gemini_key.strip():
            payload["GEMINI_API_KEY"] = gemini_key.strip()
        if openai_key.strip():
            payload["OPENAI_API_KEY"] = openai_key.strip()
        if wa_token.strip():
            payload["WHATSAPP_ACCESS_TOKEN"] = wa_token.strip()
        if exo_key.strip():
            payload["EXOTEL_API_KEY"] = exo_key.strip()
        if exo_token.strip():
            payload["EXOTEL_API_TOKEN"] = exo_token.strip()
        try:
            post("/api/settings/env", json=payload)
            st.success(
                "✅ Saved to .env. Restart the app (stop run.py and start it again) so new keys load."
            )
        except ApiError as exc:
            st.error(str(exc))
