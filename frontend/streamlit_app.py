import streamlit as st

from api import ApiError, get, post
from ui import inject_theme, require_auth, show_integrations

st.set_page_config(page_title="Smart Kitchen AI", page_icon="🍲", layout="wide")
inject_theme()
require_auth()

# ----------------- HEADER & STATUS -----------------
try:
    session_data = get("/api/flat-chat/session/today")
    members_data = get("/api/members")
except ApiError as exc:
    st.error(f"Cannot connect to Kitchen Backend: {exc}")
    st.stop()

# Flatmates list for voting
flatmates = [m["name"] for m in members_data if not m.get("is_cook")]
if not flatmates:
    flatmates = ["Shubh", "Flatmate 1", "Flatmate 2"]

cook = next((m for m in members_data if m.get("is_cook")), None)
cook_name = cook["name"] if cook else session_data.get("cook_name", "Cook")
cook_phone = cook["phone"] if (cook and cook.get("phone")) else session_data.get("cook_phone", "")

# Stage styling
stage = session_data.get("stage", "choosing_meal")
stage_info = {
    "choosing_meal": ("🟡 Voting Open", "warning", "Flatmates are choosing the meal."),
    "waiting_grocery": ("🟠 Meal Selected", "info", "A dish is picked! Check groceries and lock."),
    "confirming_order": ("🟠 Awaiting Lock", "info", "Ready to lock in the decision."),
    "locked": ("🟢 Meal Locked & Scheduled", "success", "Dinner is confirmed and ready for the cook!"),
}.get(stage, ("🟡 Active", "info", ""))

header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.title("🍲 Smart Kitchen Hub")
    st.caption(f"One-touch meal decisions & automated cook calls for flatmates • **{session_data.get('target_date_formatted', '')}**")
with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if stage == "locked":
        st.success(f"**Status:** {stage_info[0]}")
    elif stage in ("waiting_grocery", "confirming_order"):
        st.info(f"**Status:** {stage_info[0]}")
    else:
        st.warning(f"**Status:** {stage_info[0]}")

st.markdown("---")

# ----------------- VOTER IDENTITY -----------------
voter_col1, voter_col2 = st.columns([1, 2])
with voter_col1:
    current_voter = st.selectbox("👤 Who is using the app right now?", options=flatmates, index=0)
with voter_col2:
    meal_slot_title = session_data.get("meal_slot", "dinner").capitalize()
    st.markdown(f"### 🍽️ Deciding: **Tomorrow's {meal_slot_title}**")
    if session_data.get("selected_recipe_name"):
        hi_name = f" ({session_data.get('selected_recipe_hindi')})" if session_data.get("selected_recipe_hindi") else ""
        st.markdown(f"**Current Pick:** 🌟 `{session_data.get('selected_recipe_name')}{hi_name}`")
    else:
        st.markdown("_No dish selected yet. Cast your vote below!_")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- SECTION 1: THE 4 MEAL OPTIONS -----------------
st.subheader("1️⃣ Vote for Tomorrow's Meal")
st.write("Click any dish to select it for the flat, or type a custom dish below.")

options = session_data.get("options", [])
cols = st.columns(4)

for idx, opt in enumerate(options):
    with cols[idx % 4]:
        dish_name = opt.get("name", f"Option {idx+1}")
        dish_hi = opt.get("name_hi", "")
        is_current_pick = (session_data.get("selected_recipe_name") == dish_name)
        
        box_style = "border: 2px solid #22c55e; background-color: #0f291e;" if is_current_pick else "border: 1px solid #334155;"
        
        st.markdown(
            f"""
            <div style="{box_style} padding: 16px; border-radius: 12px; text-align: center; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 1.25rem;">Option {idx+1}</h3>
                <h2 style="margin: 8px 0; color: #f8fafc;">{dish_name}</h2>
                <p style="margin: 0; color: #94a3b8; font-size: 1rem;">{dish_hi}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        btn_label = f"✅ Selected" if is_current_pick else f"🗳️ Vote {dish_name}"
        if st.button(btn_label, key=f"vote_btn_{idx}", use_container_width=True, disabled=is_current_pick):
            try:
                post("/api/flat-chat/vote", json={"dish_name": dish_name, "voter": current_voter})
                st.toast(f"🎉 {current_voter} voted for {dish_name}!")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

# Custom dish option
with st.expander("✨ Want something else? Propose a custom dish"):
    c1, c2 = st.columns([3, 1])
    with c1:
        custom_dish = st.text_input("Enter dish name (e.g. Paneer Butter Masala, Rajma Chawal)", key="custom_dish_input")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Propose Dish", use_container_width=True):
            if custom_dish.strip():
                try:
                    post("/api/flat-chat/vote", json={"dish_name": custom_dish.strip(), "voter": current_voter})
                    st.success(f"Custom dish '{custom_dish}' submitted!")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 2: GROCERIES & LOCK -----------------
st.subheader("2️⃣ Confirm Groceries & Lock Meal")

g_col1, g_col2 = st.columns([1.5, 1])

with g_col1:
    st.markdown("#### 🛒 Required Groceries Checklist")
    ingredients = session_data.get("selected_ingredients", [])
    if ingredients:
        st.caption(f"Estimated ingredients for **{session_data.get('selected_recipe_name')}**:")
        for ing in ingredients:
            ing_name = ing.get("name", "").capitalize()
            qty = ing.get("qty", "")
            unit = ing.get("unit", "")
            st.checkbox(f"{ing_name} — {qty} {unit}", value=True, key=f"ing_{ing_name}")
    else:
        st.info("Pantry essentials (Oil, Salt, Spices, Atta/Rice) are ready. Check fridge for fresh veggies.")

with g_col2:
    st.markdown("#### 🔒 Lock In Decision")
    st.write("Once locked, this dish is officially synced to the kitchen calendar and ready for the cook.")
    
    if stage == "locked":
        st.success(f"🔒 **{session_data.get('selected_recipe_name')}** is LOCKED!")
        if st.button("🔄 Unlock / Re-vote", use_container_width=True):
            try:
                post("/api/flat-chat/reset")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    else:
        if st.button("🔒 Lock This Meal Now", type="primary", use_container_width=True):
            try:
                post("/api/flat-chat/lock")
                st.success("Meal locked successfully!")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 3: CALL THE COOK (EASY & 100% EDITABLE) -----------------
st.subheader("3️⃣ 📞 Call the Cook (Hindi Voice)")
st.caption("Review or edit the exact Hindi script below, then click to dial the cook's phone in real-time.")

call_col1, call_col2 = st.columns([1.5, 1])

with call_col1:
    st.markdown("#### 📝 Spoken Hindi Script (Editable)")
    default_script = session_data.get("default_hindi_script", "")
    
    # Text area allowing full customization
    edited_script = st.text_area(
        "Edit what the AI voice speaks to the cook:",
        value=default_script,
        height=120,
        help="You can add extra instructions like 'मिर्च कम रखना' or 'दही जमा देना'.",
    )

with call_col2:
    st.markdown("#### 👨‍🍳 Cook Details & Action")
    st.write(f"**Cook Name:** {cook_name}")
    dest_phone = st.text_input("Cook Phone Number:", value=cook_phone, placeholder="+919229247588")
    
    st.caption("Powered by **Twilio Voice + Amazon Polly Aditi** (fluent native Hindi).")
    
    call_btn = st.button("🚀 Call Cook Now (Ring Phone)", type="primary", use_container_width=True)
    if call_btn:
        if not dest_phone.strip():
            st.error("Please enter the cook's mobile number.")
        else:
            with st.spinner("📞 Dialing cook's phone..."):
                try:
                    res = post("/api/flat-chat/call-cook", json={"script": edited_script.strip(), "phone": dest_phone.strip()})
                    if res.get("ok"):
                        st.success(f"🎉 Call Placed! Status: **{res.get('status').upper()}**")
                        if res.get("provider_id"):
                            st.caption(f"Twilio Call SID: `{res.get('provider_id')}`")
                        st.info("The cook's phone is ringing right now!")
                    else:
                        st.warning(f"Status: {res.get('status')} — {res.get('detail')}")
                except ApiError as exc:
                    st.error(f"Call failed: {exc}")

st.markdown("---")

# ----------------- SECTION 4: QUICK AI ASSISTANT -----------------
with st.expander("🤖 Ask AI Chef / Kitchen Assistant"):
    st.caption("Ask questions about recipes, ingredients, or alternative cooking ideas.")
    if "chat" not in st.session_state:
        try:
            st.session_state.chat = get("/api/chat/history")
        except ApiError:
            st.session_state.chat = []
    
    for message in st.session_state.chat[-4:]:
        with st.chat_message(message["role"] if message["role"] in {"user", "assistant"} else "assistant"):
            st.write(message["content"])
            
    prompt = st.chat_input("Ask AI Chef (e.g. 'Can we make paneer with what we have?')...")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        try:
            result = post("/api/chat", json={"message": prompt})
            st.session_state.chat.append({"role": "assistant", "content": result.get("reply", "")})
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))
