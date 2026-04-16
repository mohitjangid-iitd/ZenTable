"""
routers/chatbot.py — Owner Dashboard Chatbot
=============================================
Endpoint : POST /api/chat
Auth     : JWT cookie (owner role only)
SDK      : google-genai (new unified SDK — pip install google-genai)

Flow:
  1. Rate limit check (20 req/min per restaurant_id, in-memory)
  2. JWT verify + owner role check
  3. Gemini Step 1 — category classify: ANALYTICS | PLATFORM_HELP | UNKNOWN
  4a. ANALYTICS    → intents detect → DB functions run → Gemini response
  4b. PLATFORM_HELP → knowledge base load → Gemini response
  4c. UNKNOWN      → friendly fallback (no Gemini call)
"""

import os
import json
import time
import glob
from collections import defaultdict
from fastapi import APIRouter, Request, HTTPException, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from google import genai
from google.genai import types

from auth import decode_token

# ── DB functions — yeh database.py mein add honge (Task 8)
from database import (
    get_today_sales,
    get_total_orders_today,
    get_top_selling_items,
    get_lowest_selling_items,
    get_revenue_summary,
)

load_dotenv()
router = APIRouter()

# ════════════════════════════════════════════════════════
# GEMINI SETUP & MULTI-MODEL ARCHITECTURE
# ════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

client = genai.Client(api_key=GEMINI_API_KEY)

# Hamara Priority Sequence (Best, 2nd Best, 3rd Best)
MODELS_TO_TRY = MODELS_TO_TRY = [
    "gemini-3.1-flash-lite-preview",  # Priority 1: 15 RPM, 500 RPD
    "gemini-2.5-flash",               # Priority 2: 5 RPM, best quality
    "gemini-3-flash-preview",         # Priority 3: 5 RPM, latest
    "gemma-4-26b-it",                 # Priority 4: 15 RPM, 1.5K RPD fallback
]

# ════════════════════════════════════════════════════════
# INTENT MAP
# ════════════════════════════════════════════════════════
# Naya intent add karna ho to:
#   1. Yahan entry add karo: "INTENT_NAME": db_function
#   2. database.py mein DB function add karo
#   3. _INTENT_PROMPT mein intent naam + example question add karo

INTENT_MAP = {
    "GET_TODAY_SALES":      get_today_sales,
    "GET_TOTAL_ORDERS":     get_total_orders_today,
    "TOP_SELLING_ITEMS":    get_top_selling_items,
    "LOWEST_SELLING_ITEMS": get_lowest_selling_items,
    "GET_REVENUE_SUMMARY":  get_revenue_summary,
}


# ════════════════════════════════════════════════════════
# RATE LIMITER — in-memory, per restaurant_id
# ════════════════════════════════════════════════════════

_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT  = 20   # max requests
RATE_WINDOW = 60   # seconds

def _check_rate_limit(restaurant_id: str) -> bool:
    """True = allowed, False = blocked"""
    now    = time.time()
    window = now - RATE_WINDOW
    _rate_store[restaurant_id] = [t for t in _rate_store[restaurant_id] if t > window]
    if len(_rate_store[restaurant_id]) >= RATE_LIMIT:
        return False
    _rate_store[restaurant_id].append(now)
    return True


# ════════════════════════════════════════════════════════
# KNOWLEDGE BASE LOADER
# ════════════════════════════════════════════════════════

_KB_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")

def _load_knowledge_base() -> str:
    """knowledge/ folder ki saari .md files ek string mein load karo"""
    files = sorted(glob.glob(os.path.join(_KB_DIR, "*.md")))
    if not files:
        return "No knowledge base available."
    parts = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                parts.append(f"### [{os.path.basename(f)}]\n{fh.read().strip()}")
        except Exception:
            pass
    return "\n\n---\n\n".join(parts)


# ════════════════════════════════════════════════════════
# PROMPTS
# ════════════════════════════════════════════════════════

_CATEGORY_PROMPT = """\
Classify the user message into exactly ONE category:
- ANALYTICS    : sales, revenue, orders, top dishes, revenue summary, performance data
- PLATFORM_HELP: how to use ZenTable, features, AR menu, staff management, pricing, setup
- UNKNOWN      : anything outside restaurant business

Reply with ONLY one word: ANALYTICS, PLATFORM_HELP, or UNKNOWN
No explanation, no punctuation, nothing else.

User message: {message}"""


_INTENT_PROMPT = """\
Detect ALL relevant intents from the user message.
Return ONLY a valid JSON array of intent strings — no explanation, no markdown.

Available intents:
- GET_TODAY_SALES       : aaj ki sales / revenue / kitna kamaya
- GET_TOTAL_ORDERS      : aaj kitne orders aaye / order count today
- TOP_SELLING_ITEMS     : sabse zyada kya bika / best sellers / popular dishes
- LOWEST_SELLING_ITEMS  : kaunsi dish nahi chal rahi / slow items / worst sellers
- GET_REVENUE_SUMMARY   : last N din ka summary / weekly report / revenue trend

Rules:
- Return JSON array only, e.g. ["GET_TODAY_SALES"] or ["TOP_SELLING_ITEMS","GET_TODAY_SALES"]
- Max 4 intents
- If nothing matches, return []

User message: {message}"""


_ANALYTICS_RESPONSE_PROMPT = """\
You are a helpful restaurant analytics assistant for ZenTable.
Answer in Hinglish (Hindi + English mix) — friendly, conversational, 2-4 sentences.

Format rules:
- Currency: Rs. format (e.g. Rs. 12,500)
- Numbers clearly stated
- No bullet points unless listing items
- No markdown formatting

Restaurant analytics data:
{data}

User question: {message}

Give a natural, helpful response based on the data."""


_PLATFORM_HELP_PROMPT = """\
You are a helpful support assistant for ZenTable restaurant management platform.
Answer in Hinglish (Hindi + English mix) — friendly, clear, step-by-step when needed.

STRICT RULES:
- Answer ONLY from the knowledge base provided below
- If answer not found: say "Yeh information mere paas nahi hai, ZenTable team se contact karo: contact@zentable.in"
- Do NOT make up features, prices, or steps
- Do NOT answer questions unrelated to ZenTable

Knowledge Base:
{knowledge}

User question: {message}"""


# ════════════════════════════════════════════════════════
# GEMINI FUNCTIONS (With Fallback Mechanism)
# ════════════════════════════════════════════════════════

def _gemini_call(prompt: str, json_mode: bool = False) -> str:
    """Try-Except loop ke sath fallback logic aur low temperature"""
    
    # Temperature 0.3 rakha hai taaki JSON output aur MD facts mein hallucination na ho
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else "text/plain",
        temperature=0.3
    )
    
    last_error = None
    
    for current_model in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config=config,
            )
            return response.text.strip()
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Agar error quota, limit ya server overload ka hai, toh agle model pe jao
            if any(keyword in error_str for keyword in ["503", "429", "overloaded", "quota", "exhausted"]):
                print(f"[Warning] {current_model} overloaded/failed. Switching to next model...")
                continue
            else:
                # Agar prompt me hi galti hai (e.g. 400 Bad Request), toh loop skip kar ke error uthao
                print(f"[Error] Failed with {current_model}: {str(e)}. Switching just in case...")
                continue

    # Agar saare models fail ho gaye
    raise HTTPException(status_code=502, detail=f"AI service error on all models. Last error: {str(last_error)}")


def _classify_category(message: str) -> str:
    """ANALYTICS | PLATFORM_HELP | UNKNOWN return karo"""
    result = _gemini_call(_CATEGORY_PROMPT.format(message=message)).upper().strip()
    if result not in ("ANALYTICS", "PLATFORM_HELP", "UNKNOWN"):
        return "UNKNOWN"
    return result


def _detect_intents(message: str) -> list[str]:
    """Valid intent strings ka list — max 4, whitelist filtered"""
    raw = _gemini_call(_INTENT_PROMPT.format(message=message), json_mode=True)
    try:
        raw = raw.strip().strip("```json").strip("```").strip()
        intents = json.loads(raw)
        if not isinstance(intents, list):
            return []
        return [i for i in intents if i in INTENT_MAP][:4]
    except Exception:
        return []

def _detect_period(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["week", "hafte", "7 din", "weekly"]):
        return "week"
    if any(w in msg for w in ["month", "mahine", "30 din", "monthly"]):
        return "month"
    if any(w in msg for w in ["alltime", "ever", "sab", "total"]):
        return "alltime"
    return "today"  # default

# ════════════════════════════════════════════════════════
# PATH HANDLERS
# ════════════════════════════════════════════════════════

def _handle_analytics(message: str, restaurant_id: str) -> str:
    intents = _detect_intents(message)

    if not intents:
        return (
            "Yeh analytics query samajh nahi aaya 😊 "
            "Aap pooch sakte hain jaise — 'Aaj ki sales?', 'Top dishes this week?', "
            "'Last 7 din ka summary?'"
        )

    combined_data = {}
    for intent in intents:
        fn = INTENT_MAP.get(intent)
        if fn:
            try:
                if intent in ("TOP_SELLING_ITEMS", "LOWEST_SELLING_ITEMS"):
                    period = _detect_period(message)  # "today"/"week"/"month"
                    combined_data[intent] = fn(restaurant_id, period=period)
                else:
                    combined_data[intent] = fn(restaurant_id)
            except Exception as e:
                combined_data[intent] = {"error": str(e)}

    return _gemini_call(
        _ANALYTICS_RESPONSE_PROMPT.format(
            message = message,
            data    = json.dumps(combined_data, ensure_ascii=False, indent=2),
        )
    )


def _handle_platform_help(message: str) -> str:
    knowledge = _load_knowledge_base()
    return _gemini_call(
        _PLATFORM_HELP_PROMPT.format(message=message, knowledge=knowledge)
    )


def _handle_unknown() -> str:
    return (
        "Yeh mere scope se bahar hai 😊 "
        "Main aapke restaurant ki analytics aur ZenTable features mein help kar sakta hoon. "
        "Kuch aur poochh sakte hain — jaise 'Aaj ki sales?' ya 'Staff kaise add karte hain?'"
    )


# ════════════════════════════════════════════════════════
# REQUEST MODEL + ENDPOINT
# ════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(
    request:    Request,
    body:       ChatRequest,
    auth_token: Optional[str] = Cookie(default=None),
):
    # ── 1. JWT verify ──
    if not auth_token:
        raise HTTPException(status_code=401, detail="Login required")

    payload = decode_token(auth_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # ── 2. Role check — sirf owner ──
    if payload.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can use this feature")

    # ── 3. restaurant_id JWT se — kabhi frontend se mat lena ──
    restaurant_id = payload.get("restaurant_id")
    if not restaurant_id:
        raise HTTPException(status_code=401, detail="Invalid token: restaurant_id missing")

    # ── 4. Rate limit ──
    if not _check_rate_limit(restaurant_id):
        raise HTTPException(
            status_code=429,
            detail="Bahut zyada requests! Ek minute baad try karo."
        )

    # ── 5. Message validate ──
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message empty hai")
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="Message bahut lamba hai (max 500 characters)")

    # ── 6. Category classify ──
    category = _classify_category(message)

    # ── 7. Path route karo ──
    if category == "ANALYTICS":
        response_text = _handle_analytics(message, restaurant_id)
    elif category == "PLATFORM_HELP":
        response_text = _handle_platform_help(message)
    else:
        response_text = _handle_unknown()

    return JSONResponse({
        "response": response_text,
        "category": category,  # debug ke liye useful
    })
