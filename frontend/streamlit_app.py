import streamlit as st
from api import ApiError, get, post, put, delete
from ui import inject_theme, require_auth

st.set_page_config(page_title="Smart Kitchen AI", page_icon="🍲", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
require_auth()

# Custom CSS for clean card-based layout
st.markdown("""
<style>
    .dish-card {
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        background: #1e293b;
        border: 2px solid #334155;
        margin-bottom: 12px;
        transition: transform 0.15s ease-in-out;
    }
    .dish-card-selected {
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        background: #064e3b;
        border: 2px solid #10b981;
        margin-bottom: 12px;
    }
    .dish-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .dish-sub {
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 0px;
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

# ----------------- TOP HEADER -----------------
head_col1, head_col2 = st.columns([2.5, 1])
with head_col1:
    st.title("🍲 Smart Kitchen")
    st.caption(f"Flat decision & automated cook calling for **{target_day_name} {meal_slot}**")
with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if is_locked:
        st.success("🔒 **Meal Locked & Confirmed**")
    elif selected_dish:
        st.info(f"🌟 **Selected:** {selected_dish}")
    else:
        st.warning("🟡 **Decision Open** — Vote Below")

st.markdown("---")

# ----------------- SECTION 1: THE FOOD MENU (FRONT & CENTER) -----------------
st.subheader(f"🍽️ What's for {meal_slot}? (Pick from the 4 Options)")
st.caption("Click any card to select it for the flat, or type a custom dish below.")

options = session_data.get("options", [])
cols = st.columns(4)

dish_emojis = ["🥞", "🍲", "🥣", "🥟", "🥘", "🍛"]

for idx, opt in enumerate(options[:4]):
    dish_name = opt.get("name", f"Option {idx+1}")
    dish_hi = opt.get("name_hi", "")
    is_picked = (selected_dish == dish_name)
    emoji = dish_emojis[idx % len(dish_emojis)]
    
    with cols[idx]:
        card_class = "dish-card-selected" if is_picked else "dish-card"
        st.markdown(
            f"""
            <div class="{card_class}">
                <div style="font-size: 2.2rem; margin-bottom: 6px;">{emoji}</div>
                <div class="dish-title">{dish_name}</div>
                <div class="dish-sub">{dish_hi}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        btn_label = "✅ Selected" if is_picked else f"Vote {dish_name}"
        if st.button(btn_label, key=f"dish_btn_{idx}", use_container_width=True, disabled=is_picked):
            try:
                post("/api/flat-chat/vote", json={"dish_name": dish_name, "voter": "Flatmate"})
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

# Quick Custom Dish Option
with st.expander("✨ Want something else? (e.g. Rajma Chawal, Paneer Butter Masala)"):
    c1, c2 = st.columns([3, 1])
    with c1:
        custom_input = st.text_input("Type any custom dish name:", placeholder="e.g. Paneer Bhurji, Dal Tadka")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Set as Meal", use_container_width=True):
            if custom_input.strip():
                try:
                    post("/api/flat-chat/vote", json={"dish_name": custom_input.strip(), "voter": "Flatmate"})
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 2: GROCERIES & MEAL LOCK (CLEAN & SIMPLE) -----------------
col_dec1, col_dec2 = st.columns([1.5, 1])

with col_dec1:
    st.subheader("🛒 Kitchen Groceries Summary")
    if selected_dish:
        ingredients = session_data.get("selected_ingredients", [])
        if ingredients:
            ing_names = [f"**{i['name'].capitalize()}** ({i.get('qty','')} {i.get('unit','')})" for i in ingredients[:6]]
            st.info(f"Items needed for **{selected_dish}**: {', '.join(ing_names)}")
        else:
            st.info(f"Kitchen essentials for **{selected_dish}** (Veggies, Oil, Spices, Atta/Rice) are ready.")
    else:
        st.write("Select a dish above to see the grocery overview.")

with col_dec2:
    st.subheader("🔒 Confirm & Lock")
    if is_locked:
        st.success(f"✅ **{selected_dish}** is officially locked for tomorrow!")
        if st.button("🔄 Unlock & Change Dish", use_container_width=True):
            try:
                post("/api/flat-chat/reset")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    else:
        if st.button("🔒 Lock This Meal Now", type="primary", use_container_width=True, disabled=not selected_dish):
            try:
                post("/api/flat-chat/lock")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

st.markdown("---")

# ----------------- SECTION 3: CALL THE COOK (EASY & 100% EDITABLE) -----------------
st.subheader("📞 Call the Cook (Hindi Voice)")
st.caption("The AI voice will speak the text below in natural Hindi. You can edit any word before calling.")

col_call1, col_call2 = st.columns([1.6, 1])

with col_call1:
    st.markdown("#### 📝 Spoken Hindi Message (Editable)")
    default_script = session_data.get("default_hindi_script", "")
    edited_script = st.text_area(
        "Edit the message the cook will hear:",
        value=default_script,
        height=110,
        help="Add any notes like 'mirch kam rakhna' or 'roti zyada banana'.",
    )

with col_call2:
    st.markdown("#### 👨‍🍳 Cook Details")
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
                                f"The number `{cook_phone_input}` has not been added to your Twilio verified list yet. "
                                f"Twilio free trial accounts can only call numbers you verify in your dashboard.\n\n"
                                f"👉 **[Click here to add & verify this number in Twilio](https://console.twilio.com/us1/develop/phone-numbers/manage/verified-caller-ids)** (Takes 30 seconds via OTP)."
                            )
                        else:
                            st.warning(f"Status: {res.get('status')} — {detail}")
                except ApiError as exc:
                    st.error(f"Call failed: {exc}")

st.markdown("---")

# ----------------- SECTION 4: FLATMATE NAMES MANAGER (MAX 6 PEOPLE) -----------------
with st.expander(f"👥 Manage Flatmates ({len(flatmates)} / 6 People)"):
    st.caption("Easily add, change, or remove flatmates anytime.")
    
    # List current flatmates
    f_cols = st.columns(min(len(flatmates), 6) or 1)
    for idx, fmate in enumerate(flatmates[:6]):
        with f_cols[idx % len(f_cols)]:
            st.markdown(f"**👤 {fmate['name']}**")
            if st.button("❌ Remove", key=f"del_fmate_{fmate['id']}"):
                try:
                    delete(f"/api/members/{fmate['id']}")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add new flatmate if under 6
    if len(flatmates) < 6:
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            new_name = st.text_input("Add New Flatmate Name:", placeholder="e.g. Aman, Priya", key="new_fmate_name")
        with add_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Add Person", use_container_width=True):
                if new_name.strip():
                    try:
                        post("/api/members", json={"name": new_name.strip(), "role": "member", "phone": "", "notify": True})
                        st.success(f"Added {new_name}!")
                        st.rerun()
                    except ApiError as exc:
                        st.error(str(exc))
    else:
        st.info("Maximum 6 flatmates reached. Remove a flatmate above to add another.")

st.markdown("---")

# ----------------- SECTION 5: AI CHEF ASSISTANT (SMART & ENGAGING) -----------------
st.subheader("🤖 Ask AI Kitchen Chef")
st.caption("Ask Chef Gemini for dinner ideas, recipe tips, or what to cook with whatever is in your fridge.")

if "chat_history" not in st.session_state:
    try:
        st.session_state["chat_history"] = get("/api/chat/history")
    except ApiError:
        st.session_state["chat_history"] = []

# Display last 4 chat messages in a clean style
for msg in st.session_state["chat_history"][-4:]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.write(msg["content"])

user_q = st.chat_input("Ask Chef (e.g. 'What can we make with paneer and onions?', 'Give me 3 light dinner ideas')...")
if user_q:
    st.session_state["chat_history"].append({"role": "user", "content": user_q})
    try:
        res = post("/api/chat", json={"message": user_q})
        st.session_state["chat_history"].append({"role": "assistant", "content": res.get("reply", "")})
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))
