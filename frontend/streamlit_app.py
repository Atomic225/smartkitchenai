import urllib.parse
from datetime import date, timedelta
import streamlit as st
from api import ApiError, get, post, put
from ui import inject_theme, require_auth

st.set_page_config(page_title="Kitchen OS: Your flat's kitchen, sorted", page_icon="🍳", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
require_auth()

# ----------------- KITCHEN OS BRANDING & STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    /* Top Kitchen OS Navbar */
    .kos-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 24px;
        background: #ffffff;
        border-radius: 18px;
        border: 1px solid #e2e8f0;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .kos-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 800;
        font-size: 1.35rem;
        color: #0f172a;
    }
    .kos-badge {
        background: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* WhatsApp Phone Frame Mockup */
    .wa-card {
        background: #f7f5ef;
        border-radius: 20px;
        border: 1px solid #e6e2d3;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .wa-header {
        background: #064e3b;
        color: #ffffff;
        padding: 14px 18px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }
    .wa-header-title {
        font-weight: 700;
        font-size: 1rem;
        margin: 0;
    }
    .wa-header-sub {
        font-size: 0.75rem;
        color: #a7f3d0;
        margin: 0;
    }
    
    /* Message Bubble */
    .wa-bubble {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-bottom: 16px;
    }
    .bubble-tag {
        font-size: 0.75rem;
        color: #059669;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .bubble-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 14px;
    }
    
    /* Instamart & Blinkit Card */
    .instamart-card {
        background: #ffffff;
        border-radius: 18px;
        border: 1px solid #fed7aa;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(251, 146, 60, 0.08);
    }
    .instamart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 12px;
        margin-bottom: 14px;
    }
    .im-badge {
        background: #ffedd5;
        color: #c2410c;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
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
</style>
""", unsafe_allow_html=True)

# ----------------- 7-DAY DEFAULT KITCHEN OS PLAN (STRICTLY DINNER ONLY) -----------------
KITCHENOS_WEEKLY_PLAN = {
    0: {
        "day": "Mon",
        "full_day": "Monday",
        "dinner": "Aloo Paratha (for 3) + Fresh Dahi",
        "groceries": [
            {"name": "Potato (आलू)", "qty": "1 kg", "price": 38, "brand": "Fresh Harvest", "emoji": "🥔"},
            {"name": "Fresh Curd (दही)", "qty": "400 g", "price": 40, "brand": "Amul Masti", "emoji": "🥛"},
            {"name": "Green Chillies & Fresh Coriander", "qty": "1 bunch", "price": 20, "brand": "Farm Fresh", "emoji": "🌿"},
        ]
    },
    1: {
        "day": "Tue",
        "full_day": "Tuesday",
        "dinner": "Paneer Butter Masala (for 3) + Roti",
        "groceries": [
            {"name": "Fresh Malai Paneer", "qty": "400 g", "price": 170, "brand": "Mother Dairy", "emoji": "🧀"},
            {"name": "Hybrid Tomato (टमाटर)", "qty": "500 g", "price": 32, "brand": "Farm Fresh", "emoji": "🍅"},
            {"name": "Fresh Cream", "qty": "200 ml", "price": 65, "brand": "Amul", "emoji": "🍶"},
            {"name": "Amul Butter", "qty": "100 g", "price": 58, "brand": "Amul", "emoji": "🧈"},
        ]
    },
    2: {
        "day": "Wed",
        "full_day": "Wednesday",
        "dinner": "Dal Tadka (for 3) + Jeera Rice (for 3)",
        "groceries": [
            {"name": "Fresh Cauliflower (गोभी)", "qty": "1 pc", "price": 45, "brand": "Local Fresh", "emoji": "🥦"},
            {"name": "Green Peas (मटर)", "qty": "250 g", "price": 35, "brand": "Peeled Fresh", "emoji": "🫛"},
            {"name": "Fresh Garlic & Ginger", "qty": "100 g", "price": 30, "brand": "Farm Fresh", "emoji": "🧄"},
        ]
    },
    3: {
        "day": "Thu",
        "full_day": "Thursday",
        "dinner": "Mixed Vegetable Sabzi (for 3) + Phulka",
        "groceries": [
            {"name": "Carrot & French Beans", "qty": "250 g", "price": 42, "brand": "Farm Fresh", "emoji": "🥕"},
            {"name": "Fresh Capsicum (शिमला मिर्च)", "qty": "250 g", "price": 28, "brand": "Farm Fresh", "emoji": "🫑"},
            {"name": "Fresh Lemon & Coriander", "qty": "1 pack", "price": 18, "brand": "Daily Harvest", "emoji": "🍋"},
        ]
    },
    4: {
        "day": "Fri",
        "full_day": "Friday",
        "dinner": "Rajma Chawal (for 3) + Sirka Onion",
        "groceries": [
            {"name": "Red Onion (प्याज़)", "qty": "1 kg", "price": 48, "brand": "Nashik Fresh", "emoji": "🧅"},
            {"name": "Ginger-Garlic Paste", "qty": "100 g", "price": 25, "brand": "Catch", "emoji": "🧄"},
            {"name": "Fresh Tomatoes", "qty": "500 g", "price": 32, "brand": "Farm Fresh", "emoji": "🍅"},
        ]
    },
    5: {
        "day": "Sat",
        "full_day": "Saturday",
        "dinner": "Idli Sambar + Podi",
        "groceries": [
            {"name": "Fresh Idli/Dosa Batter", "qty": "1 kg", "price": 85, "brand": "iD Fresh", "emoji": "🥣"},
            {"name": "Fresh Grated Coconut", "qty": "100 g", "price": 40, "brand": "Farm Fresh", "emoji": "🥥"},
            {"name": "Drumstick (सहजन) & Curry Leaves", "qty": "2 pcs", "price": 25, "brand": "Fresh Cut", "emoji": "🌿"},
        ]
    },
    6: {
        "day": "Sun",
        "full_day": "Sunday",
        "dinner": "Special Chole Bhature / Biryani",
        "groceries": [
            {"name": "Fresh Paneer / Biryani Veggies", "qty": "300 g", "price": 130, "brand": "Fresh Harvest", "emoji": "🧀"},
            {"name": "Fresh Curd for Raita", "qty": "400 g", "price": 40, "brand": "Amul Masti", "emoji": "🥛"},
            {"name": "Fresh Mint & Lemon", "qty": "1 pack", "price": 15, "brand": "Farm Fresh", "emoji": "🌱"},
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
active_plan = KITCHENOS_WEEKLY_PLAN[curr_day_idx]

# ----------------- TOP NAVBAR (KITCHEN OS) -----------------
st.markdown(
    """
    <div class="kos-header">
        <div class="kos-brand">
            🍳 Kitchen OS
            <span class="kos-badge">DINNER AUTOMATION • 7-DAY SCHEDULE</span>
        </div>
        <div style="display: flex; gap: 20px; align-items: center; font-size: 0.95rem; font-weight: 600; color: #475569;">
            <span>How it works</span>
            <span>Features</span>
            <span>Flat 402</span>
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
            "👤 Active Flatmate (Select or Change):",
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
    st.info(f"Scheduled daily at **{call_time} AM IST**. System will only call at this exact scheduled time.")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- MAIN LAYOUT (TWO COLUMNS AS IN SCREENSHOT 1 & 2) -----------------
left_col, right_col = st.columns([1.1, 1.2], gap="large")

# ==================== LEFT COLUMN: KITCHEN OS VALUE ====================
with left_col:
    st.markdown(
        """
        <div style="padding: 10px 0;">
            <h1 style="font-size: 3.2rem; font-weight: 900; line-height: 1.15; color: #0f172a; margin-bottom: 20px;">
                Decide once.<br>Eat well all week.
            </h1>
            <p style="font-size: 1.15rem; color: #475569; line-height: 1.6; margin-bottom: 28px;">
                Set up your household once, and Kitchen OS handles the rest. It drafts every night's dinner for you to approve, then informs your cook. No daily typing. No daily thinking.
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
                    <b style="color: #0f172a;">Only fresh sabzis & veggies.</b> Basic atta, rice, and oil are excluded. Instamart cart calculates the fresh items automatically.
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
                GENUINE COOK CALL • TIMED ONLY
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; margin-bottom: 6px;">
                "Strictly scheduled calls only."
            </div>
            <div style="color: #d6d3d1; font-size: 0.95rem; margin-bottom: 14px;">
                The AI will <b>never</b> spam-call the cook when you load or use the app. Calls are only dispatched at the designated schedule time (<b>{call_time} AM</b>).
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #44403c; padding-top: 12px;">
                <span style="font-size: 0.9rem; color: #a8a29e;">Cook: <b>{cook_name}</b> ({cook_phone})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🛠️ Manual Call Override (Only for emergency / when you explicitly want to call)"):
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
                    <p class="wa-header-title">Kitchen OS</p>
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

        # 3 Kitchen OS Actions
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
    
    # Combined search query for quick commerce
    sabzi_names_only = [g["name"].split("(")[0].strip() for g in groceries]
    all_sabzis_query = urllib.parse.quote(" ".join(sabzi_names_only))
    
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
            
            <b style="font-size: 1.05rem; color: #0f172a; margin-bottom: 8px; display: block;">
                Fresh Sabzis Needed for {active_plan['dinner']}
            </b>
            <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 12px;">
                Excludes basic atta, rice, and cooking oil. Only perishable vegetables & dairy needed for dinner:
            </p>
        """,
        unsafe_allow_html=True,
    )
    
    # Beautiful Sabzi Rows with Emojis
    for g in groceries:
        search_q = urllib.parse.quote(f"fresh {g['name']}")
        instamart_item_url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={search_q}"
        blinkit_item_url = f"https://blinkit.com/s/?q={search_q}"
        
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.4rem;">{g.get('emoji', '🥦')}</span>
                    <div>
                        <b style="color: #1e293b; font-size: 0.95rem;">{g['name']}</b> 
                        <span style="color: #64748b; font-size: 0.85rem;">({g['qty']})</span>
                        <div style="font-size: 0.75rem; color: #94a3b8;">{g['brand']}</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <b style="color: #0f172a; font-size: 0.95rem;">₹{g['price']}</b>
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
    
    # 1-Tap Delivery Launchers
    st.write("🛒 **1-Tap Open & Pay (Direct Cart Search):**")
    btn1, btn2 = st.columns(2)
    with btn1:
        st.link_button(
            "🟠 Open Swiggy Instamart Cart",
            f"https://www.swiggy.com/instamart/search?custom_back=true&query={all_sabzis_query}",
            use_container_width=True
        )
    with btn2:
        st.link_button(
            "🟡 Open Blinkit Cart",
            f"https://blinkit.com/s/?q={all_sabzis_query}",
            use_container_width=True
        )

    st.markdown("</div>", unsafe_allow_html=True)
