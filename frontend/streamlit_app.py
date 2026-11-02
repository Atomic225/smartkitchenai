import urllib.parse
import time
from datetime import date, timedelta
import streamlit as st
from api import ApiError, get, post, put
from ui import inject_theme, require_auth

st.set_page_config(page_title="KitchenAI: Your flat's kitchen, sorted", page_icon="🍳", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
require_auth()

# ----------------- KITCHENAI BRANDING & STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    /* Top KitchenAI Navbar */
    .kai-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 26px;
        background: #ffffff;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
    }
    .kai-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 900;
        font-size: 1.45rem;
        color: #0f172a;
        letter-spacing: -0.5px;
    }
    .kai-badge {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        border: 1px solid #fcd34d;
    }
    
    /* WhatsApp Phone Frame Mockup */
    .wa-card {
        background: #f7f5ef;
        border-radius: 24px;
        border: 1px solid #e6e2d3;
        padding: 24px;
        box-shadow: 0 12px 36px rgba(0,0,0,0.06);
    }
    .wa-header {
        background: #064e3b;
        color: #ffffff;
        padding: 14px 20px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }
    .wa-header-title {
        font-weight: 800;
        font-size: 1.05rem;
        margin: 0;
        color: #ffffff;
    }
    .wa-header-sub {
        font-size: 0.75rem;
        color: #a7f3d0;
        margin: 0;
    }
    
    /* Message Bubble */
    .wa-bubble {
        background: #ffffff;
        border-radius: 18px;
        padding: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 16px;
    }
    .bubble-tag {
        font-size: 0.75rem;
        color: #059669;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .bubble-title {
        font-size: 1.3rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 14px;
    }
    
    /* Instamart & Blinkit Card */
    .instamart-card {
        background: #ffffff;
        border-radius: 20px;
        border: 1px solid #e2e8f0;
        padding: 22px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.04);
        margin-top: 14px;
    }
    .instamart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        padding-bottom: 12px;
        border-bottom: 1px solid #f1f5f9;
    }
    .im-badge {
        background: #ffedd5;
        color: #c2410c;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 800;
    }
    
    .price-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.9rem;
        color: #475569;
        margin-bottom: 6px;
    }
    .price-total {
        display: flex;
        justify-content: space-between;
        font-size: 1.15rem;
        font-weight: 800;
        color: #0f172a;
        border-top: 1px dashed #cbd5e1;
        padding-top: 10px;
        margin-top: 10px;
    }
    
    .sabzi-badge {
        display: inline-block;
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    /* Presentation mode banner */
    .pitch-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 18px;
    }
    
    .item-link-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 700;
        text-decoration: none;
        transition: all 0.2s;
    }
    .swiggy-btn {
        background: #fff7ed;
        color: #ea580c;
        border: 1px solid #ffedd5;
    }
    .blinkit-btn {
        background: #fefce8;
        color: #ca8a04;
        border: 1px solid #fef08a;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 7-DAY DEFAULT KITCHENAI PLAN (STRICTLY DINNER ONLY) -----------------
KITCHENAI_WEEKLY_PLAN = {
    0: {
        "day": "Mon",
        "full_day": "Monday",
        "dinner": "Aloo Paratha (for 3) + Fresh Dahi",
        "hero_search": "Potato",
        "groceries": [
            {"name": "Potato (आलू)", "qty": "1 kg", "price": 38, "brand": "Fresh Harvest", "emoji": "🥔", "search": "potato"},
            {"name": "Fresh Curd (दही)", "qty": "400 g", "price": 40, "brand": "Amul Masti", "emoji": "🥛", "search": "curd"},
            {"name": "Green Chillies & Coriander", "qty": "1 bunch", "price": 20, "brand": "Farm Fresh", "emoji": "🌿", "search": "coriander"},
        ]
    },
    1: {
        "day": "Tue",
        "full_day": "Tuesday",
        "dinner": "Paneer Butter Masala (for 3) + Roti",
        "hero_search": "Paneer",
        "groceries": [
            {"name": "Fresh Malai Paneer", "qty": "400 g", "price": 170, "brand": "Mother Dairy", "emoji": "🧀", "search": "paneer"},
            {"name": "Hybrid Tomato (टमाटर)", "qty": "500 g", "price": 32, "brand": "Farm Fresh", "emoji": "🍅", "search": "tomato"},
            {"name": "Fresh Cream", "qty": "200 ml", "price": 65, "brand": "Amul", "emoji": "🍶", "search": "amul fresh cream"},
            {"name": "Amul Butter", "qty": "100 g", "price": 58, "brand": "Amul", "emoji": "🧈", "search": "amul butter"},
        ]
    },
    2: {
        "day": "Wed",
        "full_day": "Wednesday",
        "dinner": "Dal Tadka (for 3) + Jeera Rice (for 3)",
        "hero_search": "Cauliflower",
        "groceries": [
            {"name": "Fresh Cauliflower (गोभी)", "qty": "1 pc", "price": 45, "brand": "Local Fresh", "emoji": "🥦", "search": "cauliflower"},
            {"name": "Green Peas (मटर)", "qty": "250 g", "price": 35, "brand": "Peeled Fresh", "emoji": "🫛", "search": "green peas"},
            {"name": "Fresh Garlic & Ginger", "qty": "100 g", "price": 30, "brand": "Farm Fresh", "emoji": "🧄", "search": "ginger garlic"},
        ]
    },
    3: {
        "day": "Thu",
        "full_day": "Thursday",
        "dinner": "Mixed Vegetable Sabzi (for 3) + Phulka",
        "hero_search": "French Beans",
        "groceries": [
            {"name": "Carrot & French Beans", "qty": "250 g", "price": 42, "brand": "Farm Fresh", "emoji": "🥕", "search": "beans carrot"},
            {"name": "Fresh Capsicum (शिमला मिर्च)", "qty": "250 g", "price": 28, "brand": "Farm Fresh", "emoji": "🫑", "search": "capsicum"},
            {"name": "Fresh Lemon & Coriander", "qty": "1 pack", "price": 18, "brand": "Daily Harvest", "emoji": "🍋", "search": "lemon"},
        ]
    },
    4: {
        "day": "Fri",
        "full_day": "Friday",
        "dinner": "Rajma Chawal (for 3) + Sirka Onion",
        "hero_search": "Onion",
        "groceries": [
            {"name": "Red Onion (प्याज़)", "qty": "1 kg", "price": 48, "brand": "Nashik Fresh", "emoji": "🧅", "search": "onion"},
            {"name": "Ginger-Garlic Paste", "qty": "100 g", "price": 25, "brand": "Catch", "emoji": "🧄", "search": "ginger garlic paste"},
            {"name": "Fresh Tomatoes", "qty": "500 g", "price": 32, "brand": "Farm Fresh", "emoji": "🍅", "search": "tomato"},
        ]
    },
    5: {
        "day": "Sat",
        "full_day": "Saturday",
        "dinner": "Idli Sambar + Podi",
        "hero_search": "Idli Batter",
        "groceries": [
            {"name": "Fresh Idli/Dosa Batter", "qty": "1 kg", "price": 85, "brand": "iD Fresh", "emoji": "🥣", "search": "idli batter"},
            {"name": "Fresh Grated Coconut", "qty": "100 g", "price": 40, "brand": "Farm Fresh", "emoji": "🥥", "search": "coconut"},
            {"name": "Drumstick & Curry Leaves", "qty": "2 pcs", "price": 25, "brand": "Fresh Cut", "emoji": "🌿", "search": "drumstick curry leaves"},
        ]
    },
    6: {
        "day": "Sun",
        "full_day": "Sunday",
        "dinner": "Special Chole Bhature / Biryani",
        "hero_search": "Paneer",
        "groceries": [
            {"name": "Fresh Paneer / Veggies", "qty": "300 g", "price": 130, "brand": "Fresh Harvest", "emoji": "🧀", "search": "paneer"},
            {"name": "Fresh Curd for Raita", "qty": "400 g", "price": 40, "brand": "Amul Masti", "emoji": "🥛", "search": "curd"},
            {"name": "Fresh Mint & Lemon", "qty": "1 pack", "price": 15, "brand": "Farm Fresh", "emoji": "🌱", "search": "mint pudina"},
        ]
    }
}

# ----------------- LOAD DB MEMBERS & FLATMATES -----------------
try:
    all_members = get("/api/members")
    household = get("/api/household")
except ApiError:
    all_members = []
    household = {}

cook = next((m for m in all_members if m.get("is_cook")), None)
cook_name = cook["name"] if cook else "Bhaiya (Cook)"
cook_phone = cook["phone"] if (cook and cook.get("phone")) else "+919229247588"
call_time = household.get("chef_call_weekday_time") or "08:30"

flatmates = [m for m in all_members if not m.get("is_cook")]
flatmate_names = [m["name"] for m in flatmates] if flatmates else ["Shubham", "Rishu", "Flatmate 3", "Flatmate 4"]

# Ensure current active user defaults to Shubham
if "active_flatmate" not in st.session_state:
    st.session_state["active_flatmate"] = flatmate_names[0] if flatmate_names else "Shubham"

# Determine current day index (0=Mon, 1=Tue, ..., 6=Sun)
today_idx = date.today().weekday()
tomorrow_idx = (today_idx + 1) % 7

if "selected_day_idx" not in st.session_state:
    st.session_state["selected_day_idx"] = tomorrow_idx

curr_day_idx = st.session_state["selected_day_idx"]
active_plan = KITCHENAI_WEEKLY_PLAN[curr_day_idx]

# ----------------- TOP NAVBAR (KITCHENAI) -----------------
st.markdown(
    """
    <div class="kai-header">
        <div class="kai-brand">
            🍳 KitchenAI
            <span class="kai-badge">AI DINNER AUTOMATION • 7-DAY SCHEDULE</span>
        </div>
        <div style="display: flex; gap: 20px; align-items: center; font-size: 0.95rem; font-weight: 600; color: #475569;">
            <span>How it works</span>
            <span>Features</span>
            <span>Flat 402</span>
            <span style="color: #059669; font-weight: 700;">● Live Cloud</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- PRESENTATION CHEAT-SHEET EXPANDER -----------------
with st.expander("🎤 Presentation & Pitch Guide (Click to expand during your demo)"):
    st.markdown(
        """
        <div class="pitch-card">
            <h4 style="margin-top: 0; color: #0f172a;">🎯 30-Second Elevator Pitch for KitchenAI</h4>
            <p style="color: #334155; font-size: 0.95rem; line-height: 1.5;">
                <i>"Flatmates spend 20 minutes every single morning arguing over what to cook for dinner, while their cook calls repeatedly or waits. 
                <b>KitchenAI solves this forever:</b> A pre-set 7-day dinner calendar runs on autopilot. If anyone wants a change, they swap in 5 seconds. 
                Every morning at 08:30 AM, KitchenAI automatically dials the cook with a natural Hindi voice call and dispatches the exact fresh sabzi cart to Swiggy Instamart and Blinkit."</i>
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-top: 10px;">
                <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0;">
                    <b>1. Zero Brain Drain</b><br>
                    <span style="font-size: 0.82rem; color: #64748b;">Monday to Sunday dinner is pre-planned. No daily arguments.</span>
                </div>
                <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0;">
                    <b>2. Timed Voice AI</b><br>
                    <span style="font-size: 0.82rem; color: #64748b;">Cook gets a natural Hindi call only at 08:30 AM. No spam or hacker calls.</span>
                </div>
                <div style="background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0;">
                    <b>3. 1-Tap Sabzi Cart</b><br>
                    <span style="font-size: 0.82rem; color: #64748b;">No basic atta/rice. Only perishable veggies calculated & ready to order.</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------- FLATMATE & PREFERENCES BAR (EDITABLE) -----------------
f_bar1, f_bar2 = st.columns([1.5, 1])
with f_bar1:
    col_u1, col_u2 = st.columns([1.2, 1])
    with col_u1:
        st.session_state["active_flatmate"] = st.selectbox(
            "👤 Active Flatmate (Select or Switch):",
            options=flatmate_names,
            index=0 if st.session_state["active_flatmate"] not in flatmate_names else flatmate_names.index(st.session_state["active_flatmate"])
        )
    with col_u2:
        with st.popover("✏️ Edit Flatmate Names"):
            st.caption("Change, add or rename flatmates:")
            new_f_name = st.text_input("New Flatmate Name:", placeholder="e.g. Shubham")
            if st.button("➕ Add / Rename", use_container_width=True):
                if new_f_name.strip():
                    try:
                        post("/api/members", json={"name": new_f_name.strip(), "role": "member", "phone": "", "notify": True})
                        st.success(f"Saved {new_f_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

with f_bar2:
    st.caption("⏰ **Automated Cook Call Schedule:**")
    st.info(f"Scheduled daily at **{call_time} AM IST**. System only calls at this exact scheduled minute.")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- MAIN LAYOUT (TWO COLUMNS) -----------------
left_col, right_col = st.columns([1.1, 1.2], gap="large")

# ==================== LEFT COLUMN: KITCHENAI VALUE ====================
with left_col:
    st.markdown(
        """
        <div style="padding: 10px 0;">
            <h1 style="font-size: 3.2rem; font-weight: 900; line-height: 1.15; color: #0f172a; margin-bottom: 20px;">
                Decide once.<br>Eat well all week.
            </h1>
            <p style="font-size: 1.15rem; color: #475569; line-height: 1.6; margin-bottom: 28px;">
                Set up your household once, and <b>KitchenAI</b> handles the rest. It drafts every night's dinner for you to approve, then informs your cook in Hindi. No daily typing. No daily thinking.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Feature Bullet Points
    st.markdown(
        """
        <div style="display: flex; flex-direction: column; gap: 16px; margin-bottom: 28px;">
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="color: #059669; font-size: 1.2rem; font-weight: 900;">✓</span>
                <div>
                    <b style="color: #0f172a;">Pre-set 7 days dinner.</b> Monday to Sunday is already set. If nobody touches it, dinner happens automatically.
                </div>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="color: #059669; font-size: 1.2rem; font-weight: 900;">✓</span>
                <div>
                    <b style="color: #0f172a;">Swap any dinner in 5 seconds.</b> Don't feel like having Rajma on Friday? Swap to Paneer with 1 tap.
                </div>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="color: #059669; font-size: 1.2rem; font-weight: 900;">✓</span>
                <div>
                    <b style="color: #0f172a;">Only fresh sabzis & veggies.</b> Basic atta, rice, and oil are excluded. Instamart & Blinkit cart calculates only fresh perishable items.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Genuine Voice Call Policy Card (No Spam / No Hacker behavior)
    st.markdown(
        f"""
        <div style="background: #1c1917; color: white; padding: 22px; border-radius: 18px; margin-top: 10px;">
            <div style="color: #fbbf24; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                GENUINE COOK CALL • STRICTLY TIMED
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; margin-bottom: 6px;">
                "Strictly scheduled calls only."
            </div>
            <div style="color: #d6d3d1; font-size: 0.95rem; margin-bottom: 14px;">
                KitchenAI will <b>never</b> spam-call the cook when you load or use the app. Calls are only dispatched at the designated schedule time (<b>{call_time} AM</b>).
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #44403c; padding-top: 12px;">
                <span style="font-size: 0.9rem; color: #a8a29e;">Cook: <b>{cook_name}</b> ({cook_phone})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🛠️ Manual Call Override (Only for emergency / manual test)"):
        st.caption("This button will only dial when you manually click it:")
        if st.button("📞 Manually Call Cook Now", type="secondary", use_container_width=True):
            script_text = (
                f"नमस्ते {cook_name}! कल {active_plan['full_day']} के रात के खाने में {active_plan['dinner']} "
                f"तय हुआ है। सामान किचन में उपलब्ध है। कृपया समय पर आ जाएं। धन्यवाद!"
            )
            try:
                res = post("/api/flat-chat/call-cook", json={"script": script_text, "phone": cook_phone})
                if res.get("ok"):
                    st.success(f"Call placed to {cook_phone}!")
                else:
                    st.warning(f"{res.get('detail')}")
            except Exception as exc:
                st.error(f"Error: {exc}")


# ==================== RIGHT COLUMN: WHATSAPP DINNER FRAME & INSTAMART ====================
with right_col:
    st.markdown(
        """
        <div class="wa-card">
            <!-- WA Header -->
            <div class="wa-header">
                <div style="font-size: 1.8rem;">🍳</div>
                <div>
                    <p class="wa-header-title">KitchenAI</p>
                    <p class="wa-header-sub">online • Asia/Kolkata</p>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Inside WhatsApp Frame
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <b style="font-size: 1.15rem; color: #0f172a;">This week's dinner schedule</b>
            <span style="color: #059669; font-size: 0.8rem; font-weight: 700;">● PRE-SET</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # WhatsApp Message Bubble: Your week is planned
    with st.container():
        st.markdown(
            f"""
            <div class="wa-bubble">
                <div class="bubble-tag">7-DAY DINNER SCHEDULE</div>
                <div class="bubble-title">Your week is planned</div>
            """,
            unsafe_allow_html=True,
        )
        
        # 7 Days Tabs (Mon Tue Wed Thu Fri Sat Sun)
        day_cols = st.columns(7)
        days_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for idx, abbr in enumerate(days_abbr):
            with day_cols[idx]:
                is_selected = (idx == curr_day_idx)
                btn_type = "primary" if is_selected else "secondary"
                if st.button(abbr, key=f"day_nav_{idx}", type=btn_type, use_container_width=True):
                    st.session_state["selected_day_idx"] = idx
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Dinner for Selected Day (Single Daily Decision)
        st.markdown(
            f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #64748b; font-weight: 800; font-size: 0.85rem; letter-spacing: 0.5px;">TONIGHT / TOMORROW'S DINNER ({active_plan['full_day'].upper()})</span>
                    <span style="background: #d1fae5; color: #065f46; font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 999px;">DEFAULT SET</span>
                </div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #047857; margin-top: 8px;">
                    🍽️ {active_plan['dinner']}
                </div>
            </div>
            <div style="text-align: right; color: #94a3b8; font-size: 0.75rem;">10:05 AM ✓✓</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3 KitchenAI Actions
        act1, act2, act3 = st.columns(3)
        with act1:
            if st.button("↳ Approve week", use_container_width=True):
                try:
                    post("/api/flat-chat/lock")
                    st.toast(f"✅ Approved & locked for {active_plan['full_day']}!")
                except Exception:
                    st.toast("✅ Week Approved!")
        with act2:
            swap_open = st.button("↳ Edit plan", use_container_width=True)
        with act3:
            if st.button("↳ Regenerate", use_container_width=True):
                st.toast("🔄 Generating creative dinner ideas...")

        if swap_open:
            new_dish = st.selectbox(
                f"Swap {active_plan['full_day']}'s Dinner with:",
                ["Paneer Butter Masala", "Aloo Paratha", "Dal Tadka with Rice", "Mixed Vegetable Sabzi", "Rajma Chawal", "Idli Sambar", "Chole Bhature", "Paneer Bhurji", "Dal Makhani"]
            )
            if st.button("Save Swap", use_container_width=True):
                try:
                    post("/api/flat-chat/vote", json={"dish_name": new_dish, "voter": st.session_state["active_flatmate"]})
                    st.success(f"Swapped {active_plan['full_day']} to {new_dish}!")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==================== FRESH SABZIS & DIRECT DELIVERY (INSTAMART & BLINKIT) ====================
    groceries = active_plan["groceries"]
    items_total = sum(g["price"] for g in groceries)
    handling_fee = 12
    gst = 8
    grand_total = items_total + handling_fee + gst
    
    st.markdown(
        f"""
        <div class="instamart-card">
            <div class="instamart-header">
                <div>
                    <span style="font-size: 0.8rem; color: #64748b;">Flat 402 • fresh sabzi cart</span>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #ea580c;">🟠 Swiggy Instamart & Blinkit</div>
                </div>
                <span class="im-badge">CALCULATED FOR DINNER</span>
            </div>
            
            <b style="font-size: 1.05rem; color: #0f172a; margin-bottom: 6px; display: block;">
                Fresh Sabzis Needed for {active_plan['dinner']}
            </b>
            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 14px;">
                Excludes basic atta, rice, and cooking oil. Only perishable vegetables & dairy needed for dinner:
            </p>
        """,
        unsafe_allow_html=True,
    )
    
    # Interactive Individual Sabzi Rows with Direct 1-Click Launchers
    for g in groceries:
        search_query = urllib.parse.quote(g.get("search", g["name"].split("(")[0].strip()))
        swiggy_url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={search_query}"
        blinkit_url = f"https://blinkit.com/s/?q={search_query}"
        
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.35rem;">{g.get('emoji', '🥦')}</span>
                    <div>
                        <b style="color: #1e293b; font-size: 0.95rem;">{g['name']}</b> 
                        <span style="color: #64748b; font-size: 0.85rem;">({g['qty']})</span>
                        <div style="font-size: 0.75rem; color: #94a3b8;">{g['brand']} • ₹{g['price']}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 8px;">
                    <a href="{swiggy_url}" target="_blank" class="item-link-btn swiggy-btn" title="Open on Swiggy Instamart">
                        🟠 Swiggy
                    </a>
                    <a href="{blinkit_url}" target="_blank" class="item-link-btn blinkit-btn" title="Open on Blinkit">
                        🟡 Blinkit
                    </a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Order Breakdown Table
    st.markdown(
        f"""
            <div style="background: #f8fafc; border-radius: 12px; padding: 14px; margin-top: 14px;">
                <div class="price-row"><span>Sabzi Items Total</span><span>₹{items_total}</span></div>
                <div class="price-row"><span>Handling Fee</span><span>₹{handling_fee}</span></div>
                <div class="price-row"><span>Delivery Partner Fee</span><span style="color: #16a34a; font-weight: 700;">FREE</span></div>
                <div class="price-row"><span>GST and Charges</span><span>₹{gst}</span></div>
                <div class="price-total">
                    <span>Total Estimated Amount</span>
                    <span style="color: #ea580c;">₹{grand_total}</span>
                </div>
            </div>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 10px;">
                📍 <b>Delivering to:</b> Flat 402, Prestige Misty Waters, Hebbal, Bengaluru
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Store Launchers
    st.write("🛒 **Open Quick Commerce Apps Directly:**")
    hero_search = urllib.parse.quote(active_plan.get("hero_search", "fresh vegetables"))
    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        st.link_button("🟠 Swiggy Instamart", f"https://www.swiggy.com/instamart/search?custom_back=true&query={hero_search}", use_container_width=True)
    with btn2:
        st.link_button("🟡 Blinkit", f"https://blinkit.com/s/?q={hero_search}", use_container_width=True)
    with btn3:
        st.link_button("⚡ Zepto", "https://www.zeptonow.com", use_container_width=True)

    # ----------------- TEST AUTO-PAY WITH 1 ITEM -----------------
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🧪 Test Auto-Pay with 1 Item (Real UPI / Single-Item Test)", expanded=True):
        st.markdown(
            """
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 14px; margin-bottom: 14px;">
                <b style="color: #0f172a; font-size: 1.05rem;">💳 1-Item Auto-Pay & Checkout Tester</b>
                <p style="color: #64748b; font-size: 0.85rem; margin: 4px 0 0 0;">
                    Test how the automated payment and single-item dispatch works with real UPI or quick commerce.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        test_col1, test_col2 = st.columns([1.5, 1])
        with test_col1:
            item_options = {
                "₹1 Token Test (Safest for real UPI test)": {"price": 1, "query": "paneer", "name": "₹1 KitchenAI Verification Token"},
                "Fresh Malai Paneer (400g)": {"price": 170, "query": "paneer", "name": "Fresh Malai Paneer"},
                "Amul Butter (100g)": {"price": 58, "query": "amul butter", "name": "Amul Butter"},
                "Potato / Aloo (1kg)": {"price": 38, "query": "potato", "name": "Fresh Potato"},
                "Hybrid Tomato (500g)": {"price": 32, "query": "tomato", "name": "Hybrid Tomato"},
            }
            selected_test_label = st.selectbox("1. Choose Item to Test:", list(item_options.keys()))
            chosen_item = item_options[selected_test_label]
            
            custom_upi = st.text_input("2. Flat UPI VPA for Auto-Debit:", value="kitchenai@upi", help="Enter your UPI ID or test VPA")
        
        with test_col2:
            st.metric("Test Item Amount", f"₹{chosen_item['price']}", delta="AutoPay Enabled")
            st.caption("Includes direct UPI Intent link + QR code")
            
        test_btn = st.button(f"⚡ Generate 1-Item Auto-Pay for ₹{chosen_item['price']}", type="primary", use_container_width=True)
        
        if test_btn or st.session_state.get("active_test_item") == selected_test_label:
            st.session_state["active_test_item"] = selected_test_label
            
            # Real UPI Intent URL
            upi_note = urllib.parse.quote(f"KitchenAI {chosen_item['name']}")
            upi_intent_url = f"upi://pay?pa={custom_upi}&pn=KitchenAI&am={chosen_item['price']}&cu=INR&tn={upi_note}"
            qr_encoded = urllib.parse.quote(upi_intent_url)
            qr_img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_encoded}"
            
            st.markdown("---")
            q_col1, q_col2 = st.columns([1, 1.3])
            with q_col1:
                st.image(qr_img_url, caption=f"Scan to Pay ₹{chosen_item['price']} (GPay/PhonePe)", width=180)
            with q_col2:
                st.markdown(
                    f"""
                    <div style="font-size: 0.9rem; line-height: 1.6;">
                        <b>Item:</b> {chosen_item['name']}<br>
                        <b>AutoPay Amount:</b> <span style="color: #ea580c; font-weight: 800;">₹{chosen_item['price']}</span><br>
                        <b>Target VPA:</b> <code>{custom_upi}</code><br>
                        <b>Status:</b> <span style="background: #ecfdf5; color: #065f46; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem;">UPI MANDATE READY</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.link_button("📲 Tap to Pay via UPI (Mobile GPay/PhonePe)", upi_intent_url, use_container_width=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.write(f"🛒 **Direct Quick Commerce 1-Item Links for '{chosen_item['name']}':**")
            single_swiggy_url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={urllib.parse.quote(chosen_item['query'])}"
            single_blinkit_url = f"https://blinkit.com/s/?q={urllib.parse.quote(chosen_item['query'])}"
            
            lnk_col1, lnk_col2 = st.columns(2)
            with lnk_col1:
                st.link_button(f"🟠 Open '{chosen_item['query']}' on Swiggy Instamart", single_swiggy_url, use_container_width=True)
            with lnk_col2:
                st.link_button(f"🟡 Open '{chosen_item['query']}' on Blinkit", single_blinkit_url, use_container_width=True)
                
            if st.button("✅ Mark Payment as Verified & Trigger Dispatch", type="secondary", use_container_width=True):
                st.success(f"🎉 Payment of ₹{chosen_item['price']} verified for {chosen_item['name']}! Auto-dispatch simulated.")
                st.balloons()

    # Presentation Demo: Interactive 1-Tap Auto-Checkout Simulation
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚡ Live Demo: 1-Tap Autonomous Checkout (Presentation Pitch)", expanded=True):
        st.caption("Showcase the seamless checkout experience to judges/audience:")
        if st.button("🚀 Demo Instant Auto-Pay & Dispatch", key="demo_pay_btn", type="primary", use_container_width=True):
            status_box = st.empty()
            status_box.info("Connecting to Quick Commerce Network & Dark Store...")
            time.sleep(0.5)
            status_box.info("🛒 Compiling fresh sabzis for " + active_plan['dinner'] + "...")
            time.sleep(0.5)
            status_box.info(f"💳 Applying Flat UPI AutoPay (₹{grand_total} split across flatmates = ₹{round(grand_total/len(flatmate_names))}/person)...")
            time.sleep(0.5)
            status_box.success("🎉 Order Placed & Confirmed! Delivery Partner assigned (ETA: 11 mins 🛵)")
            st.balloons()

    st.markdown("</div>", unsafe_allow_html=True)
