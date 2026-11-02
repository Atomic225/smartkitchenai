import urllib.parse
import streamlit as st
from api import ApiError, get, post, put, delete
from ui import inject_theme, require_auth

st.set_page_config(page_title="Smart Kitchen AI", page_icon="🍲", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
require_auth()

# Custom CSS for clean card-based layout
st.markdown("""
<style>
    .default-hero {
        padding: 24px;
        border-radius: 16px;
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
        border: 2px solid #10b981;
        margin-bottom: 24px;
    }
    .dish-card {
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        background: #1e293b;
        border: 1px solid #334155;
        margin-bottom: 8px;
    }
    .dish-card-active {
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        background: #064e3b;
        border: 2px solid #10b981;
        margin-bottom: 8px;
    }
    .sabzi-row {
        background: #1e293b;
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- LOAD DATA -----------------
try:
    session_data = get("/api/flat-chat/session/today")
    all_members = get("/api/members")
except ApiError as exc:
    st.error(f"Cannot connect to Kitchen Backend: {exc}")
    st.stop()

flatmates = [m for m in all_members if not m.get("is_cook")]
cook = next((m for m in all_members if m.get("is_cook")), None)

cook_name = cook["name"] if cook else "Bhaiya (Cook)"
cook_phone = cook["phone"] if (cook and cook.get("phone")) else "+919229247588"

selected_dish = session_data.get("selected_recipe_name", "")
is_locked = (session_data.get("stage") == "locked")
target_day_name = session_data.get("target_date_formatted", "Tomorrow")
meal_slot = session_data.get("meal_slot", "dinner").capitalize()
fresh_sabzis = session_data.get("fresh_sabzis", [])

# 7-Day Static Guide
WEEKLY_ROUTINE = [
    ("Monday", "🥞 Aloo Paratha + Dahi"),
    ("Tuesday", "🥘 Paneer Butter Masala"),
    ("Wednesday", "🍛 Dal Tadka & Rice"),
    ("Thursday", "🍲 Mixed Veg Sabzi"),
    ("Friday", "🫘 Rajma Chawal"),
    ("Saturday", "🥟 Idli Sambar"),
    ("Sunday", "🥘 Chole Bhature"),
]

# ----------------- 1. HERO: PRE-PLANNED DEFAULT MEAL -----------------
st.markdown(
    f"""
    <div class="default-hero">
        <div style="font-size: 0.95rem; text-transform: uppercase; letter-spacing: 1.5px; color: #6ee7b7; font-weight: 700;">
            📅 PRE-PLANNED 7-DAY SCHEDULE • {target_day_name.upper()}
        </div>
        <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin: 8px 0;">
            {selected_dish}
        </div>
        <div style="font-size: 1.05rem; color: #d1fae5;">
            ✅ <b>This is set as the default meal for tomorrow.</b> If no one changes it, our cook will prepare this!
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- 2. QUICK SWAP / ALTERNATIVE OPTIONS -----------------
with st.expander("🔄 Want to change tomorrow's dish? Tap any option to switch", expanded=False):
    st.caption("Anyone in the flat can change tomorrow's dish with 1 click:")
    opts = session_data.get("options", [])
    opt_cols = st.columns(len(opts) if opts else 1)
    for idx, opt in enumerate(opts):
        with opt_cols[idx]:
            d_name = opt.get("name", "")
            d_hi = opt.get("name_hi", "")
            is_active = (d_name == selected_dish)
            cls = "dish-card-active" if is_active else "dish-card"
            st.markdown(
                f"""
                <div class="{cls}">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #fff;">{d_name}</div>
                    <div style="color: #94a3b8; font-size: 0.9rem;">{d_hi}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if not is_active:
                if st.button(f"Switch to {d_name}", key=f"switch_opt_{idx}", use_container_width=True):
                    try:
                        post("/api/flat-chat/vote", json={"dish_name": d_name, "voter": "Flatmate"})
                        st.rerun()
                    except ApiError as exc:
                        st.error(str(exc))
            else:
                st.caption("✅ Currently Selected")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        custom_input = st.text_input("Or enter a completely custom dish:", placeholder="e.g. Paneer Bhurji, Dal Makhani")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Set Custom Dish", use_container_width=True):
            if custom_input.strip():
                try:
                    post("/api/flat-chat/vote", json={"dish_name": custom_input.strip(), "voter": "Flatmate"})
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

st.markdown("---")

# ----------------- 3. SMART FRESH SABZIS & 1-CLICK ZEPTO/BLINKIT -----------------
st.subheader(f"🛒 Fresh Sabzis & Veggies Needed for {selected_dish}")
st.caption("Basic items (Atta, Rice, Oil, Salt, Haldi) are automatically ignored. Only fresh perishable veggies & dairy are listed:")

if fresh_sabzis:
    for idx, item in enumerate(fresh_sabzis):
        item_name = item.get("name", "").capitalize()
        qty = item.get("qty", "")
        unit = item.get("unit", "")
        
        # URL encode for direct app search
        search_term = urllib.parse.quote(f"fresh {item.get('name', '')}")
        blinkit_url = f"https://blinkit.com/s/?q={search_term}"
        zepto_url = f"https://www.zeptonow.com/search?query={search_term}"
        
        row_c1, row_c2, row_c3 = st.columns([2, 1, 1])
        with row_c1:
            st.markdown(f"🥦 **{item_name}** — `{qty} {unit}`")
        with row_c2:
            st.link_button(f"🟡 Blinkit: {item_name}", blinkit_url, use_container_width=True)
        with row_c3:
            st.link_button(f"🟣 Zepto: {item_name}", zepto_url, use_container_width=True)
else:
    st.info(f"Pantry essentials for {selected_dish} are standard. No special perishable veggies needed.")

st.markdown("---")

# ----------------- 4. CALL THE COOK (HINDI VOICE) -----------------
st.subheader("📞 Call the Cook (Hindi Voice)")
st.caption("Spoken instructions automatically include the meal and fresh sabzi details:")

call_c1, call_c2 = st.columns([1.6, 1])
with call_c1:
    default_script = session_data.get("default_hindi_script", "")
    edited_script = st.text_area(
        "Spoken Hindi Message (Editable):",
        value=default_script,
        height=100,
        help="Feel free to add any custom instructions like 'mirch kam rakhna' before calling.",
    )
with call_c2:
    st.write(f"**Cook:** {cook_name}")
    cook_phone_input = st.text_input("Cook Phone Number:", value=cook_phone)
    st.caption("Powered by **Twilio Voice (`Polly.Aditi` Hindi)**")
    
    if st.button("🚀 Call Cook Now (Ring Phone)", type="primary", use_container_width=True):
        if not cook_phone_input.strip():
            st.error("Please enter the cook's phone number.")
        else:
            with st.spinner("📞 Dialing cook..."):
                try:
                    res = post("/api/flat-chat/call-cook", json={"script": edited_script.strip(), "phone": cook_phone_input.strip()})
                    if res.get("ok"):
                        st.success(f"🎉 Calling {cook_phone_input}! Status: **{res.get('status').upper()}**")
                        if res.get("provider_id"):
                            st.caption(f"Call SID: `{res.get('provider_id')}`")
                    else:
                        detail = res.get("detail", "")
                        if "573002" in detail or "verified recipient" in detail.lower():
                            st.error(
                                f"⚠️ **Twilio Trial Account Restriction:**\n\n"
                                f"The number `{cook_phone_input}` has not been added to your Twilio verified list yet.\n\n"
                                f"👉 **[Click here to add & verify this number in Twilio](https://console.twilio.com/us1/develop/phone-numbers/manage/verified-caller-ids)**"
                            )
                        else:
                            st.warning(f"Status: {res.get('status')} — {detail}")
                except ApiError as exc:
                    st.error(f"Call failed: {exc}")

st.markdown("---")

# ----------------- 5. VIEW FULL 7-DAY DEFAULT SCHEDULE -----------------
with st.expander("📅 View Full 7-Day Pre-Planned Schedule (Monday – Sunday)"):
    st.caption("This is your flat's recurring weekly routine. It automatically rotates day by day:")
    w_cols = st.columns(7)
    for idx, (day, dish) in enumerate(WEEKLY_ROUTINE):
        with w_cols[idx]:
            st.markdown(f"**{day}**")
            st.info(dish)
