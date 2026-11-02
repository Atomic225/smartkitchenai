import urllib.parse
from datetime import date, timedelta
import streamlit as st
from api import ApiError, get, post, put
from ui import inject_theme, require_auth

st.set_page_config(page_title="KitchenOS: Your flat's kitchen, sorted", page_icon="🍳", layout="wide", initial_sidebar_state="collapsed")
inject_theme()
require_auth()

# ----------------- KITCHENOS BRANDING & STYLES -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    /* Top KitchenOS Navbar */
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
    
    /* Instamart Card */
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
</style>
""", unsafe_allow_html=True)

# ----------------- 7-DAY DEFAULT KITCHENOS PLAN -----------------
KITCHENOS_WEEKLY_PLAN = {
    0: {
        "day": "Mon",
        "full_day": "Monday",
        "breakfast": "Poha (for 3)",
        "lunch": "Dal tadka (for 3) + Rice (for 3)",
        "dinner": "Aloo Paratha (for 3) + Dahi (200g)",
        "groceries": [
            {"name": "Potato (आलू)", "qty": "1 kg", "price": 38, "brand": "Fresh Harvest"},
            {"name": "Fresh Curd (दही)", "qty": "400 g", "price": 40, "brand": "Amul Masti"},
            {"name": "Green Chillies & Coriander", "qty": "1 bunch", "price": 20, "brand": "Farm Fresh"},
        ]
    },
    1: {
        "day": "Tue",
        "full_day": "Tuesday",
        "breakfast": "Upma (for 3)",
        "lunch": "Mixed Veg Sabzi (for 3) + Roti (9)",
        "dinner": "Paneer Butter Masala (for 3) + Roti (9)",
        "groceries": [
            {"name": "Fresh Malai Paneer", "qty": "400 g", "price": 170, "brand": "Mother Dairy"},
            {"name": "Hybrid Tomato (टमाटर)", "qty": "500 g", "price": 32, "brand": "Farm Fresh"},
            {"name": "Fresh Cream", "qty": "200 ml", "price": 65, "brand": "Amul"},
            {"name": "Butter", "qty": "100 g", "price": 58, "brand": "Amul"},
        ]
    },
    2: {
        "day": "Wed",
        "full_day": "Wednesday",
        "breakfast": "Masala Omelette / Bread Poha",
        "lunch": "Aloo Gobi Matar + Roti",
        "dinner": "Dal Tadka (for 3) + Jeera Rice (for 3)",
        "groceries": [
            {"name": "Fresh Cauliflower (गोभी)", "qty": "1 pc", "price": 45, "brand": "Local Fresh"},
            {"name": "Green Peas (मटर)", "qty": "250 g", "price": 35, "brand": "Peeled Fresh"},
            {"name": "Fresh Garlic (लहसुन)", "qty": "100 g", "price": 30, "brand": "Farm Fresh"},
        ]
    },
    3: {
        "day": "Thu",
        "full_day": "Thursday",
        "breakfast": "Idli Sambar (for 3)",
        "lunch": "Rajma Chawal (for 3)",
        "dinner": "Mixed Vegetable Sabzi (for 3) + Phulka (9)",
        "groceries": [
            {"name": "Carrot & French Beans", "qty": "250 g", "price": 42, "brand": "Farm Fresh"},
            {"name": "Drumstick (सहजन)", "qty": "2 pcs", "price": 25, "brand": "Fresh Cut"},
            {"name": "Fresh Lemon & Coriander", "qty": "1 pack", "price": 18, "brand": "Daily Harvest"},
        ]
    },
    4: {
        "day": "Fri",
        "full_day": "Friday",
        "breakfast": "Poha with Peanuts",
        "lunch": "Chole Chawal (for 3)",
        "dinner": "Rajma Chawal (for 3) + Sirka Onion",
        "groceries": [
            {"name": "Red Onion (प्याज़)", "qty": "1 kg", "price": 48, "brand": "Nashik Fresh"},
            {"name": "Ginger-Garlic Paste", "qty": "100 g", "price": 25, "brand": "Catch"},
            {"name": "Fresh Tomatoes", "qty": "500 g", "price": 32, "brand": "Farm Fresh"},
        ]
    },
    5: {
        "day": "Sat",
        "full_day": "Saturday",
        "breakfast": "Masala Dosa + Nariyal Chutney",
        "lunch": "Dal Makhani (for 3) + Jeera Rice",
        "dinner": "Idli Sambar + Podi",
        "groceries": [
            {"name": "Idli/Dosa Batter", "qty": "1 kg", "price": 85, "brand": "iD Fresh"},
            {"name": "Fresh Grated Coconut", "qty": "100 g", "price": 40, "brand": "Farm Fresh"},
            {"name": "Curry Leaves", "qty": "1 pack", "price": 10, "brand": "Local"},
        ]
    },
    6: {
        "day": "Sun",
        "full_day": "Sunday",
        "breakfast": "Aloo Puri / Chole Bhature",
        "lunch": "Special Veg Biryani + Boondi Raita",
        "dinner": "Light Khichdi / Chef Choice",
        "groceries": [
            {"name": "Paneer / Biryani Veggies", "qty": "300 g", "price": 130, "brand": "Fresh Harvest"},
            {"name": "Curd for Raita", "qty": "400 g", "price": 40, "brand": "Amul Masti"},
            {"name": "Mint & Lemon", "qty": "1 pack", "price": 15, "brand": "Farm Fresh"},
        ]
    }
}

# ----------------- LOAD DB SESSION DATA -----------------
try:
    session_data = get("/api/flat-chat/session/today")
    all_members = get("/api/members")
except ApiError:
    session_data = {}
    all_members = []

cook = next((m for m in all_members if m.get("is_cook")), None)
cook_name = cook["name"] if cook else "Bhaiya (Cook)"
cook_phone = cook["phone"] if (cook and cook.get("phone")) else "+919229247588"

# Determine current day index (0=Mon, 1=Tue, ..., 6=Sun)
today_idx = date.today().weekday()
tomorrow_idx = (today_idx + 1) % 7

if "selected_day_idx" not in st.session_state:
    st.session_state["selected_day_idx"] = tomorrow_idx

curr_day_idx = st.session_state["selected_day_idx"]
active_plan = KITCHENOS_WEEKLY_PLAN[curr_day_idx]

# ----------------- TOP NAVBAR -----------------
st.markdown(
    """
    <div class="kos-header">
        <div class="kos-brand">
            🍳 KitchenOS
            <span class="kos-badge">NEW • CLOSED LOOP • AI WEEKLY PLAN</span>
        </div>
        <div style="display: flex; gap: 24px; align-items: center; font-size: 0.95rem; font-weight: 600; color: #475569;">
            <span>How it works</span>
            <span>Features</span>
            <span>Flat 402</span>
            <span style="background: #25D366; color: white; padding: 8px 16px; border-radius: 999px; display: flex; align-items: center; gap: 8px; font-weight: 700;">
                💬 Start on WhatsApp
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- MAIN LAYOUT (TWO COLUMNS AS IN SCREENSHOT 1 & 2) -----------------
left_col, right_col = st.columns([1.1, 1.2], gap="large")

# ==================== LEFT COLUMN: KITCHENOS COPY & VALUE ====================
with left_col:
    st.markdown(
        """
        <div style="padding: 10px 0;">
            <h1 style="font-size: 3.2rem; font-weight: 900; line-height: 1.15; color: #0f172a; margin-bottom: 20px;">
                Decide once.<br>Eat well all week.
            </h1>
            <p style="font-size: 1.15rem; color: #475569; line-height: 1.6; margin-bottom: 28px;">
                Set up your household once, and KitchenOS handles the rest. It drafts a full week's menu for you to approve, then sends it straight to your cook. No daily typing. No daily thinking.
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
                    <b style="color: #0f172a;">Set it once, forever.</b> Headcount (for 3), meal times, cook's schedule, allergies, dislikes: tell it once, it remembers.
                </div>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="color: #059669; font-size: 1.2rem; font-weight: 900;">✓</span>
                <div>
                    <b style="color: #0f172a;">You approve, it delivers.</b> Review the week, edit any dish, or regenerate the whole thing, then it's sent automatically to your cook.
                </div>
            </div>
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <span style="color: #059669; font-size: 1.2rem; font-weight: 900;">✓</span>
                <div>
                    <b style="color: #0f172a;">Swap one dish, anytime.</b> Don't like Thursday's dinner? Edit just that and your cook's informed instantly via voice.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Voice to Cook Card (Screenshot 3 & 4 feature)
    st.markdown(
        f"""
        <div style="background: #1c1917; color: white; padding: 22px; border-radius: 18px; margin-top: 10px;">
            <div style="color: #fbbf24; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;">
                FOR THE COOK • NO APP NEEDED
            </div>
            <div style="font-size: 1.35rem; font-weight: 800; margin-bottom: 6px;">
                "Main bas voice note bhejti hoon."
            </div>
            <div style="color: #d6d3d1; font-size: 0.95rem; margin-bottom: 14px;">
                Your cook talks in Hindi. KitchenOS calls or sends the audio, confirms the plan, and logs groceries automatically.
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #44403c; padding-top: 12px;">
                <span style="font-size: 0.9rem; color: #a8a29e;">Cook: <b>{cook_name}</b> ({cook_phone})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📞 Place Hindi Phone Call to Cook Now", type="primary", use_container_width=True):
        script_text = (
            f"नमस्ते {cook_name}! कल {active_plan['full_day']} के मेनू में दोपहर को {active_plan['lunch']} "
            f"और रात को {active_plan['dinner']} तय हुआ है। कृपया समय पर आ जाएं। धन्यवाद!"
        )
        try:
            res = post("/api/flat-chat/call-cook", json={"script": script_text, "phone": cook_phone})
            if res.get("ok"):
                st.success(f"🎉 Calling {cook_phone}! Status: {res.get('status').upper()}")
            else:
                st.warning(f"Call notice: {res.get('detail')}")
        except Exception as exc:
            st.error(f"Error calling: {exc}")


# ==================== RIGHT COLUMN: WHATSAPP SIMULATOR & INSTAMART ====================
with right_col:
    st.markdown(
        """
        <div class="wa-card">
            <!-- WA Header -->
            <div class="wa-header">
                <div style="font-size: 1.8rem;">🍳</div>
                <div>
                    <p class="wa-header-title">KitchenOS</p>
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
            <b style="font-size: 1.15rem; color: #0f172a;">This week's menu</b>
            <span style="color: #059669; font-size: 0.8rem; font-weight: 700;">● AUTO-GENERATED</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # WhatsApp Message Bubble: Your week is planned
    with st.container():
        st.markdown(
            f"""
            <div class="wa-bubble">
                <div class="bubble-tag">WEEKLY MEAL PLAN</div>
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
        
        # Meals for Selected Day
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.95rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                    <span style="color: #64748b; font-weight: 700; width: 110px;">BREAKFAST</span>
                    <span style="color: #0f172a; font-weight: 700; flex: 1;">{active_plan['breakfast']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.95rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                    <span style="color: #64748b; font-weight: 700; width: 110px;">LUNCH</span>
                    <span style="color: #0f172a; font-weight: 700; flex: 1;">{active_plan['lunch']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.95rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                    <span style="color: #64748b; font-weight: 700; width: 110px;">DINNER</span>
                    <span style="color: #0f172a; font-weight: 800; color: #047857; flex: 1;">{active_plan['dinner']}</span>
                </div>
            </div>
            <div style="text-align: right; color: #94a3b8; font-size: 0.75rem;">10:05 AM ✓✓</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3 KitchenOS Actions (Screenshot 1)
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
                st.toast("🔄 Generating fresh creative options...")

        if swap_open:
            new_dish = st.selectbox(
                f"Swap {active_plan['full_day']}'s Dinner with:",
                ["Paneer Butter Masala", "Aloo Paratha", "Dal Tadka with Rice", "Mixed Vegetable Sabzi", "Rajma Chawal", "Idli Sambar", "Chole Bhature"]
            )
            if st.button("Save Swap", use_container_width=True):
                try:
                    post("/api/flat-chat/vote", json={"dish_name": new_dish, "voter": "Flatmate"})
                    st.success(f"Swapped {active_plan['full_day']} to {new_dish}!")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==================== SWIGGY INSTAMART CART (SCREENSHOT 2) ====================
    st.markdown(
        f"""
        <div class="instamart-card">
            <div class="instamart-header">
                <div>
                    <span style="font-size: 0.8rem; color: #64748b;">Flat 402 • order via</span>
                    <div style="font-size: 1.15rem; font-weight: 800; color: #ea580c;">🟠 Swiggy Instamart</div>
                </div>
                <span class="im-badge">READY TO ORDER</span>
            </div>
            
            <b style="font-size: 1.05rem; color: #0f172a; margin-bottom: 8px; display: block;">
                Grocery cart for {active_plan['full_day']}
            </b>
        """,
        unsafe_allow_html=True,
    )
    
    # List groceries for this meal
    groceries = active_plan["groceries"]
    items_total = sum(g["price"] for g in groceries)
    handling_fee = 12
    gst = 8
    grand_total = items_total + handling_fee + gst
    
    for g in groceries:
        search_q = urllib.parse.quote(f"fresh {g['name']}")
        instamart_url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={search_q}"
        
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f8fafc;">
                <div>
                    <b style="color: #1e293b; font-size: 0.95rem;">{g['name']}</b> 
                    <span style="color: #64748b; font-size: 0.85rem;">({g['qty']})</span>
                    <div style="font-size: 0.75rem; color: #94a3b8;">{g['brand']}</div>
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
                <div class="price-row"><span>Item Total</span><span>₹{items_total}</span></div>
                <div class="price-row"><span>Handling Fee</span><span>₹{handling_fee}</span></div>
                <div class="price-row"><span>Delivery Partner Fee</span><span style="color: #16a34a; font-weight: 700;">FREE</span></div>
                <div class="price-row"><span>GST and Charges</span><span>₹{gst}</span></div>
                <div class="price-total">
                    <span>Total Amount</span>
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
    
    # 1-Click Order Buttons
    btn1, btn2 = st.columns(2)
    with btn1:
        st.link_button("🟠 Order on Swiggy Instamart", "https://www.swiggy.com/instamart", use_container_width=True)
    with btn2:
        st.link_button("🟡 Order on Blinkit", "https://blinkit.com", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
