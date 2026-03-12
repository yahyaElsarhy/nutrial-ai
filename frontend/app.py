"""
NutriAI - Streamlit Frontend
Hybrid UI: Static Form + Chat Interface
Author: Senior AI Engineer
"""

import streamlit as st
import requests
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="NutriAI",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0f1117;
    color: #e8e8e0;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; }
.nutriai-logo {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #a8d5a2;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
}
.nutriai-tagline {
    font-size: 0.75rem;
    color: #5a7a5a;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}
[data-testid="stSidebar"] {
    background: #13191a;
    border-right: 1px solid #1e2a1e;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }
.section-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: #a8d5a2;
    margin-bottom: 1rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1e3a1e;
}
.info-card {
    background: #13191a;
    border: 1px solid #1e2e1e;
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.day-card {
    background: #111a11;
    border-left: 3px solid #4a8a4a;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.day-title {
    font-family: 'Playfair Display', serif;
    color: #a8d5a2;
    font-size: 1rem;
    margin-bottom: 0.6rem;
}
.meal-row {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    margin-bottom: 0.3rem;
    font-size: 0.88rem;
}
.meal-label {
    color: #5a8a5a;
    font-weight: 500;
    min-width: 80px;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.meal-text { color: #c8d8c0; }
.meal-cal  { color: #4a7a4a; font-size: 0.78rem; margin-left: auto; }
.chat-user {
    background: #1a2e1a;
    border: 1px solid #2a4a2a;
    border-radius: 12px 12px 2px 12px;
    padding: 0.7rem 1rem;
    margin: 0.5rem 0 0.5rem 20%;
    font-size: 0.9rem;
    color: #d0e8d0;
}
.chat-bot {
    background: #131a13;
    border: 1px solid #1e2e1e;
    border-radius: 12px 12px 12px 2px;
    padding: 0.7rem 1rem;
    margin: 0.5rem 20% 0.5rem 0;
    font-size: 0.9rem;
    color: #b0c8b0;
}
.chat-label {
    font-size: 0.7rem;
    color: #3a5a3a;
    margin-bottom: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.macro-bar {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}
.macro-item {
    flex: 1;
    background: #111a11;
    border: 1px solid #1e2e1e;
    border-radius: 8px;
    padding: 0.8rem;
    text-align: center;
}
.macro-value {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: #a8d5a2;
}
.macro-label {
    font-size: 0.7rem;
    color: #4a6a4a;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.stButton > button {
    background: #2a5a2a !important;
    color: #c8e8c0 !important;
    border: 1px solid #3a7a3a !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #3a7a3a !important;
    border-color: #4a9a4a !important;
}
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #13191a !important;
    border: 1px solid #1e3a1e !important;
    color: #e0e8e0 !important;
    border-radius: 6px !important;
}
.disclaimer {
    background: #1a1510;
    border: 1px solid #3a2a10;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.8rem;
    color: #8a7a50;
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "token":        None,
        "username":     None,
        "session_id":   None,
        "sessions":     [],
        "diet_plan":    None,
        "chat_history": [],
        "page":         "auth",
        "provider":     "groq",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def api_post(path, payload, auth=False):
    headers = auth_headers() if auth else {}
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=payload, headers=headers, timeout=120)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend. Is the server running?"}, 503

def api_get(path, auth=True):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", headers=auth_headers() if auth else {}, timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend."}, 503

def api_delete(path):
    try:
        r = requests.delete(f"{BACKEND_URL}{path}", headers=auth_headers(), timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot connect to backend."}, 503


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 - AUTH PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_auth():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="nutriai-logo">🥗 NutriAI</div>', unsafe_allow_html=True)
        st.markdown('<div class="nutriai-tagline">Personalized Clinical Nutrition</div>', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Login", "Register"])
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            username = st.text_input("Username", key="login_user", placeholder="your_username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
            if st.button("Login →", use_container_width=True):
                if not username or not password:
                    st.error("Please fill all fields.")
                else:
                    data, code = api_post("/auth/login", {"username": username, "password": password})
                    if code == 200:
                        st.session_state.token    = data["access_token"]
                        st.session_state.username = username
                        st.session_state.page     = "form"
                        _load_sessions()
                        st.rerun()
                    else:
                        st.error(data.get("detail", "Login failed"))
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            r_user  = st.text_input("Username", key="reg_user",  placeholder="choose a username")
            r_email = st.text_input("Email",    key="reg_email", placeholder="you@email.com")
            r_pass  = st.text_input("Password", type="password", key="reg_pass", placeholder="min 6 chars")
            if st.button("Create Account →", use_container_width=True):
                if not r_user or not r_email or not r_pass:
                    st.error("Please fill all fields.")
                else:
                    data, code = api_post("/auth/register", {"username": r_user, "email": r_email, "password": r_pass})
                    if code == 201:
                        st.success("Account created! Please login.")
                    else:
                        st.error(data.get("detail", "Registration failed"))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 - SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def _load_sessions():
    data, code = api_get("/sessions")
    if code == 200:
        st.session_state.sessions = data.get("sessions", [])

def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="nutriai-logo" style="font-size:1.4rem">🥗 NutriAI</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="nutriai-tagline">@{st.session_state.username}</div>', unsafe_allow_html=True)
        st.session_state.provider = st.selectbox(
            "AI Provider", ["groq", "openrouter"],
            index=0 if st.session_state.provider == "groq" else 1,
        )
        st.divider()
        if st.button("+ New Diet Plan", use_container_width=True):
            data, code = api_post("/sessions/new", {}, auth=True)
            if code == 200:
                st.session_state.session_id   = data["session_id"]
                st.session_state.diet_plan    = None
                st.session_state.chat_history = []
                st.session_state.page         = "form"
                _load_sessions()
                st.rerun()
            else:
                st.error("Could not create session")
        st.markdown("**Previous Plans**")
        _load_sessions()
        for s in st.session_state.sessions:
            sid     = s["session_id"]
            created = s["created_at"][:10]
            col_pill, col_del = st.columns([5, 1])
            with col_pill:
                if st.button(f"📋 {created} ...{sid[-6:]}", key=f"sess_{sid}", use_container_width=True):
                    st.session_state.session_id = sid
                    st.session_state.page       = "chat"
                    data, _ = api_get(f"/chat/history/{sid}")
                    st.session_state.chat_history = [
                        m for m in data.get("history", []) if m["role"] != "system"
                    ]
                    st.rerun()
            with col_del:
                if st.button("✕", key=f"del_{sid}"):
                    api_delete(f"/sessions/{sid}")
                    if st.session_state.session_id == sid:
                        st.session_state.session_id   = None
                        st.session_state.diet_plan    = None
                        st.session_state.chat_history = []
                        st.session_state.page         = "form"
                    _load_sessions()
                    st.rerun()
        st.divider()
        if st.button("Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            init_state()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 - DIET FORM
# ══════════════════════════════════════════════════════════════════════════════

def render_form():
    st.markdown('<div class="section-header">Your Health Profile</div>', unsafe_allow_html=True)
    st.markdown("Fill in your details to generate a personalized 15-day meal plan.")
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    age    = c1.number_input("Age",         min_value=10,  max_value=100, value=30)
    height = c2.number_input("Height (cm)", min_value=100, max_value=250, value=170)
    weight = c3.number_input("Weight (kg)", min_value=30,  max_value=300, value=70)
    gender = c4.selectbox("Gender", ["Male", "Female", "Other"])
    c5, c6 = st.columns(2)
    activity = c5.selectbox("Activity Level", [
        "sedentary", "light", "moderate", "active", "very_active"
    ], format_func=lambda x: {
        "sedentary":   "🪑 Sedentary (desk job)",
        "light":       "🚶 Light (1-3 days/week)",
        "moderate":    "🏃 Moderate (3-5 days/week)",
        "active":      "💪 Active (6-7 days/week)",
        "very_active": "🔥 Very Active (athlete)",
    }[x])
    goal = c6.selectbox("Goal", [
        "lose_weight", "maintain", "gain_muscle"
    ], format_func=lambda x: {
        "lose_weight": "⬇️ Lose Weight",
        "maintain":    "⚖️ Maintain Weight",
        "gain_muscle": "⬆️ Gain Muscle",
    }[x])
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header" style="font-size:1.1rem">Medical Conditions</div>', unsafe_allow_html=True)
    mc1, mc2, mc3, mc4 = st.columns(4)
    diabetes         = mc1.checkbox("🩸 Diabetes")
    hypertension     = mc2.checkbox("❤️ Hypertension")
    high_cholesterol = mc3.checkbox("🫀 High Cholesterol")
    thyroid          = mc4.checkbox("🦋 Thyroid Disorder")
    other_conditions = st.text_input("Other medical conditions", placeholder="e.g. IBS, GERD...")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header" style="font-size:1.1rem">Allergies & Intolerances</div>', unsafe_allow_html=True)
    allergies_options = ["Nuts", "Shellfish", "Eggs", "Soy", "Fish", "Sesame", "Peanuts"]
    allergies = st.multiselect("Food Allergies", allergies_options)
    custom_allergy = st.text_input("Other allergies", placeholder="e.g. mango, strawberry...")
    if custom_allergy:
        allergies += [a.strip() for a in custom_allergy.split(",")]
    il1, il2 = st.columns(2)
    lactose = il1.checkbox("🥛 Lactose Intolerance")
    gluten  = il2.checkbox("🌾 Gluten Intolerance")
    other_intolerances = st.text_input("Other intolerances", placeholder="e.g. fructose...")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header" style="font-size:1.1rem">Diet & Medications</div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    diet_type = d1.selectbox("Diet Preference", ["regular", "vegetarian", "vegan", "keto"],
        format_func=lambda x: {
            "regular": "🍽️ Regular", "vegetarian": "🥦 Vegetarian",
            "vegan": "🌱 Vegan", "keto": "🥑 Keto",
        }[x])
    medications   = d2.text_input("Current Medications", placeholder="e.g. Metformin 500mg...")
    special_notes = st.text_area("Special Notes", placeholder="Any additional information for the nutritionist...", height=80)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🌿 Generate My 15-Day Meal Plan", use_container_width=True):
        if not st.session_state.session_id:
            data, code = api_post("/sessions/new", {}, auth=True)
            if code != 200:
                st.error("Could not create session. Please try again.")
                return
            st.session_state.session_id = data["session_id"]
        profile = {
            "age": age, "gender": gender.lower(),
            "height_cm": height, "weight_kg": weight,
            "activity_level": activity, "goal": goal,
            "diabetes": diabetes, "hypertension": hypertension,
            "high_cholesterol": high_cholesterol, "thyroid_disorder": thyroid,
            "other_conditions": other_conditions, "allergies": allergies,
            "lactose_intolerance": lactose, "gluten_intolerance": gluten,
            "other_intolerances": other_intolerances,
            "medications": medications, "diet_type": diet_type,
            "special_notes": special_notes,
        }
        with st.spinner("🧠 Analyzing your health profile and generating your personalized plan..."):
            data, code = api_post("/diet/generate", {
                "session_id": st.session_state.session_id,
                "profile":    profile,
                "provider":   st.session_state.provider,
            }, auth=True)
        if code == 200:
            st.session_state.diet_plan    = data["diet_plan"]
            st.session_state.chat_history = []
            st.session_state.page         = "chat"
            _load_sessions()
            st.rerun()
        else:
            st.error(f"Error: {data.get('detail', 'Generation failed')}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 - DIET PLAN DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def render_diet_plan(plan: dict):
    st.markdown('<div class="section-header">Your Personalized 15-Day Plan</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="info-card">' + plan.get("user_profile_summary", "") + '</div>',
        unsafe_allow_html=True,
    )

    macros = plan.get("macros", {})
    st.markdown(
        '<div class="macro-bar">'
        '<div class="macro-item"><div class="macro-value">' + plan.get("daily_calories", "—") + '</div><div class="macro-label">Calories / Day</div></div>'
        '<div class="macro-item"><div class="macro-value">' + macros.get("protein", "—") + '</div><div class="macro-label">Protein</div></div>'
        '<div class="macro-item"><div class="macro-value">' + macros.get("carbs", "—") + '</div><div class="macro-label">Carbs</div></div>'
        '<div class="macro-item"><div class="macro-value">' + macros.get("fat", "—") + '</div><div class="macro-label">Fat</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    adjustments = plan.get("medical_adjustments", [])
    if adjustments:
        adj_html = " &nbsp;·&nbsp; ".join(["✓ " + a for a in adjustments])
        st.markdown(
            '<div class="info-card" style="font-size:0.82rem; color:#6a9a6a;">' + adj_html + '</div>',
            unsafe_allow_html=True,
        )

    meal_plan = plan.get("meal_plan", [])
    if meal_plan:
        # Build HTML strings completely outside any column context
        left_html  = ""
        right_html = ""

        for i, day_data in enumerate(meal_plan):
            meals     = day_data.get("meals", {})
            day_title = day_data.get("day", "Day " + str(i + 1))

            meals_html = ""
            for meal_name in ["breakfast", "lunch", "dinner", "snack"]:
                m = meals.get(meal_name, {})
                if m:
                    meals_html += (
                        '<div class="meal-row">'
                        '<span class="meal-label">' + meal_name + '</span>'
                        '<span class="meal-text">'  + m.get("meal", "") + '</span>'
                        '<span class="meal-cal">'   + m.get("calories", "") + ' kcal</span>'
                        '</div>'
                    )

            card = (
                '<div class="day-card">'
                '<div class="day-title">' + day_title + '</div>'
                + meals_html +
                '</div>'
            )

            if i % 2 == 0:
                left_html  += card
            else:
                right_html += card

        # Single st.markdown per column — the ONLY correct way in Streamlit
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(left_html,  unsafe_allow_html=True)
        with col_right:
            st.markdown(right_html, unsafe_allow_html=True)

    disclaimer = plan.get("disclaimer", "")
    if disclaimer:
        st.markdown(
            '<div class="disclaimer">⚠️ ' + disclaimer + '</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 - CHAT INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def render_chat():
    # Diet plan rendered at top level — NOT inside any st.columns() block
    # This means the st.columns(2) inside render_diet_plan is only 1 level deep
    if st.session_state.diet_plan:
        render_diet_plan(st.session_state.diet_plan)
    else:
        st.info("No diet plan loaded for this session.")
        if st.button("← Create New Plan"):
            st.session_state.page = "form"
            st.rerun()

    st.divider()

    # Chat below the plan
    st.markdown('<div class="section-header">Chat with NutriAI</div>', unsafe_allow_html=True)
    st.markdown("Ask me anything about your meal plan, substitutions, or nutrition.")

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                '<div class="chat-user"><div class="chat-label">You</div>' + msg["content"] + '</div>',
                unsafe_allow_html=True,
            )
        elif msg["role"] == "assistant":
            st.markdown(
                '<div class="chat-bot"><div class="chat-label">🥗 NutriAI</div>' + msg["content"] + '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    user_input = st.text_area(
        "Your message",
        placeholder="e.g. Can I substitute chicken with tofu on Day 3?",
        height=90,
        key="chat_input",
        label_visibility="collapsed",
    )

    c_send, c_clear = st.columns([3, 1])
    with c_send:
        if st.button("Send →", use_container_width=True):
            if not user_input.strip():
                st.warning("Please type a message.")
            elif not st.session_state.session_id:
                st.error("No active session.")
            else:
                with st.spinner("Thinking..."):
                    data, code = api_post("/chat", {
                        "session_id": st.session_state.session_id,
                        "message":    user_input.strip(),
                        "provider":   st.session_state.provider,
                    }, auth=True)
                if code == 200:
                    st.session_state.chat_history = [
                        m for m in data.get("history", []) if m["role"] != "system"
                    ]
                    st.rerun()
                else:
                    st.error(data.get("detail", "Chat failed"))
    with c_clear:
        if st.button("Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not st.session_state.token:
        render_auth()
        return
    render_sidebar()
    if st.session_state.page == "form":
        render_form()
    elif st.session_state.page == "chat":
        render_chat()
    else:
        render_form()

if __name__ == "__main__":
    main()
