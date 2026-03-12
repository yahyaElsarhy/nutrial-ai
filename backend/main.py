"""
NutriAI - Intelligent Personalized Diet Recommendation System
Backend: FastAPIsd
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from backend.providers.groq_provider import GroqProvider
from backend.providers.openai_provider import OpenAIProvider

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nutriai")

# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════════════

load_dotenv()

GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
JWT_SECRET         = os.getenv("JWT_SECRET", "nutriai-secret-key-change-in-prod")
JWT_ALGORITHM      = "HS256"
JWT_EXPIRE_HOURS   = 24

# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="NutriAI API",
    description="Personalized AI Diet Recommendation System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ── In-Memory Stores (swap with DB in production) ────────────────────────────
users_db:    dict = {}   # { username: { password, email } }
sessions_db: dict = {}   # { session_id: { username, history, diet_plan, created_at } }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 ─ SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    email:    str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    age:             int
    gender:          str
    height_cm:       float
    weight_kg:       float
    activity_level:  str        # sedentary / light / moderate / active / very_active
    goal:            str        # lose_weight / maintain / gain_muscle

    # Medical
    diabetes:          bool = False
    hypertension:      bool = False
    high_cholesterol:  bool = False
    thyroid_disorder:  bool = False
    other_conditions:  Optional[str] = ""

    # Allergies & Intolerances
    allergies:           List[str] = []
    lactose_intolerance: bool = False
    gluten_intolerance:  bool = False
    other_intolerances:  Optional[str] = ""

    # Medications & Diet
    medications:   Optional[str] = ""
    diet_type:     str = "regular"   # keto / vegetarian / vegan / regular
    special_notes: Optional[str] = ""

class GeneratePlanRequest(BaseModel):
    session_id: str
    profile:    UserProfile
    provider:   str = "groq"   # groq | openrouter

class ChatRequest(BaseModel):
    session_id: str
    message:    str
    provider:   str = "groq"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 ─ AUTH UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return decode_token(credentials.credentials)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 ─ PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
You are a certified clinical nutrition assistant.

Your task is to generate a personalized 15-day meal plan based strictly on the user's structured health data.

Clinical Safety Rules:
- If Diabetes = yes: Limit simple sugars, prefer low glycemic index carbs, distribute carbs evenly.
- If Hypertension = yes: Limit sodium, avoid processed/canned foods, emphasize potassium-rich foods.
- If High Cholesterol = yes: Reduce saturated fats, avoid fried food, increase fiber.
- If Lactose intolerance: Avoid dairy, use lactose-free or plant alternatives.
- If Gluten intolerance: Avoid wheat, barley, rye — use gluten-free alternatives.
- Strictly exclude any listed allergy items.
- Never include food that conflicts with medical conditions.
- If medical case is complex, add a stronger medical disclaimer.

CRITICAL OUTPUT RULES:
- You MUST respond with ONLY a valid JSON object.
- Do NOT include any markdown, code fences, explanation, or text outside the JSON.
- Your entire response must start with { and end with }.
- Every string value must be properly quoted and escaped.
- Do NOT use single quotes; use double quotes only.
"""


def build_diet_user_prompt(p: UserProfile) -> str:
    allergies_str = ", ".join(p.allergies) if p.allergies else "None"

    variables = (
        "User Data:\n"
        "Age: {age}\n"
        "Gender: {gender}\n"
        "Height: {height_cm} cm\n"
        "Weight: {weight_kg} kg\n"
        "Activity Level: {activity_level}\n"
        "Goal: {goal}\n"
        "\n"
        "Medical Conditions:\n"
        "- Diabetes: {diabetes}\n"
        "- Hypertension: {hypertension}\n"
        "- High Cholesterol: {high_cholesterol}\n"
        "- Thyroid Disorder: {thyroid_disorder}\n"
        "- Other Conditions: {other_conditions}\n"
        "\n"
        "Food Allergies: {allergies}\n"
        "\n"
        "Food Intolerances:\n"
        "- Lactose intolerance: {lactose}\n"
        "- Gluten intolerance: {gluten}\n"
        "- Other intolerances: {other_intolerances}\n"
        "\n"
        "Medications: {medications}\n"
        "Diet Preference: {diet_type}\n"
        "Special Notes: {special_notes}\n"
    ).format(
        age                = p.age,
        gender             = p.gender,
        height_cm          = p.height_cm,
        weight_kg          = p.weight_kg,
        activity_level     = p.activity_level,
        goal               = p.goal,
        diabetes           = "yes" if p.diabetes           else "no",
        hypertension       = "yes" if p.hypertension       else "no",
        high_cholesterol   = "yes" if p.high_cholesterol   else "no",
        thyroid_disorder   = "yes" if p.thyroid_disorder   else "no",
        other_conditions   = p.other_conditions   or "None",
        allergies          = allergies_str,
        lactose            = "yes" if p.lactose_intolerance else "no",
        gluten             = "yes" if p.gluten_intolerance  else "no",
        other_intolerances = p.other_intolerances or "None",
        medications        = p.medications        or "None",
        diet_type          = p.diet_type,
        special_notes      = p.special_notes      or "None",
    )

    schema = """
Generate a complete 15-day meal plan as a JSON object matching this schema exactly.
Return ONLY the JSON object — no markdown, no code fences, no explanation.
Your entire response must start with { and end with }.

{
  "user_profile_summary": "string",
  "daily_calories": "string",
  "macros": { "protein": "string", "carbs": "string", "fat": "string" },
  "medical_adjustments": ["string"],
  "meal_plan": [
    {
      "day": "Day 1",
      "meals": {
        "breakfast": { "meal": "string", "calories": "string", "notes": "string" },
        "lunch":     { "meal": "string", "calories": "string", "notes": "string" },
        "dinner":    { "meal": "string", "calories": "string", "notes": "string" },
        "snack":     { "meal": "string", "calories": "string", "notes": "string" }
      }
    }
  ],
  "disclaimer": "string"
}

The meal_plan array MUST contain exactly 15 items (Day 1 through Day 15).
Respond with ONLY the JSON object. No other text.
"""

    return variables + schema


CHAT_SYSTEM_PROMPT = """\
You are NutriAI, a friendly clinical nutrition assistant.
The user has already received a personalized 15-day diet plan.
Answer their follow-up questions about their diet plan, nutrition, ingredients, or substitutions.
Keep answers concise, practical, and medically safe.
If asked about something outside nutrition/diet, politely redirect."""


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 ─ PROVIDER FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_provider(name: str):
    if name == "groq":
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")
        return GroqProvider(api_key=GROQ_API_KEY)
    elif name == "openrouter":
        if not OPENROUTER_API_KEY:
            raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not configured")
        return OpenAIProvider(api_key=OPENROUTER_API_KEY)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {name!r}. Use 'groq' or 'openrouter'.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 ─ JSON PARSER UTILITY
# ══════════════════════════════════════════════════════════════════════════════

def parse_llm_json(raw: str) -> dict:
    clean = raw.strip()

    # Fix double braces from model output
    clean = clean.replace("{{", "{").replace("}}", "}")

    if "```json" in clean:
        clean = clean.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif "```" in clean:
        clean = clean.split("```", 1)[1].rsplit("```", 1)[0].strip()

    start = clean.find("{")
    end   = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")

    clean = clean[start:end]

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        snippet = clean[max(0, e.pos - 60): e.pos + 60]
        raise ValueError(f"JSON decode error at pos {e.pos}: {e.msg}\n...{snippet}...")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 ─ AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    if req.username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    users_db[req.username] = {
        "password": req.password,   # Hash with bcrypt in production
        "email":    req.email,
    }
    logger.info("Registered new user: %s", req.username)
    return {"message": "User registered successfully"}


@app.post("/auth/login")
def login(req: LoginRequest):
    user = users_db.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(req.username)
    logger.info("User logged in: %s", req.username)
    return {"access_token": token, "token_type": "bearer"}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 ─ SESSION ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/sessions/new")
def new_session(username: str = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    sessions_db[session_id] = {
        "username":   username,
        "history":    [],
        "diet_plan":  None,
        "created_at": datetime.utcnow().isoformat(),
    }
    logger.info("New session %s for user %s", session_id, username)
    return {"session_id": session_id}


@app.get("/sessions")
def list_sessions(username: str = Depends(get_current_user)):
    user_sessions = [
        {"session_id": sid, "created_at": data["created_at"]}
        for sid, data in sessions_db.items()
        if data["username"] == username
    ]
    return {"sessions": user_sessions}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, username: str = Depends(get_current_user)):
    session = sessions_db.get(session_id)
    if not session or session["username"] != username:
        raise HTTPException(status_code=404, detail="Session not found")
    del sessions_db[session_id]
    return {"message": "Session deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 ─ DIET PLAN GENERATION
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/diet/generate")
async def generate_diet_plan(
    req: GeneratePlanRequest,
    username: str = Depends(get_current_user),
):
    session = sessions_db.get(req.session_id)
    if not session or session["username"] != username:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info("Generating diet plan for user=%s session=%s provider=%s",
                username, req.session_id, req.provider)

    provider     = get_provider(req.provider)
    user_prompt  = build_diet_user_prompt(req.profile)

    raw_response = await provider.chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=16000,
    )

    logger.debug("RAW LLM RESPONSE (first 800 chars):\n%s", raw_response[:800])

    try:
        diet_plan = parse_llm_json(raw_response)
    except ValueError as e:
        logger.error("JSON parse failed.\nError: %s\nFull raw response:\n%s", e, raw_response)
        raise HTTPException(
            status_code=500,
            detail=f"LLM returned invalid JSON: {e}",
        )

    # Basic schema validation — catch empty/wrong responses early
    if "meal_plan" not in diet_plan:
        logger.error("Parsed JSON missing 'meal_plan' key. Got keys: %s", list(diet_plan.keys()))
        raise HTTPException(status_code=500, detail="LLM response missing required 'meal_plan' key")

    session["diet_plan"] = diet_plan
    session["history"] = [
        {"role": "system",    "content": CHAT_SYSTEM_PROMPT},
        {"role": "assistant", "content": "I've generated your 15-day meal plan. Ask me anything about it!"},
    ]

    logger.info("Diet plan generated successfully for session=%s", req.session_id)
    return {"diet_plan": diet_plan}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 ─ CHAT (Conversation Memory)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/chat")
async def chat(
    req: ChatRequest,
    username: str = Depends(get_current_user),
):
    session = sessions_db.get(req.session_id)
    if not session or session["username"] != username:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.get("diet_plan"):
        raise HTTPException(status_code=400, detail="Generate a diet plan first")

    session["history"].append({"role": "user", "content": req.message})

    provider = get_provider(req.provider)
    reply = await provider.chat_with_history(
        messages=session["history"].copy(),
        temperature=0.7,
    )

    session["history"].append({"role": "assistant", "content": reply})

    return {
        "reply":   reply,
        "history": session["history"],
    }


@app.get("/chat/history/{session_id}")
def get_history(session_id: str, username: str = Depends(get_current_user)):
    session = sessions_db.get(session_id)
    if not session or session["username"] != username:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"history": session["history"]}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 ─ HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status":    "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version":   "1.0.0",
        "providers": {
            "groq":       bool(GROQ_API_KEY),
            "openrouter": bool(OPENROUTER_API_KEY),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 ─ ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

# uvicorn backend.main:app --reload
# venv\Scripts\activate
# streamlit run frontend/app.py