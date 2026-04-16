"""
routers/help_chat.py — Landing Page Public Chatbot
===================================================
Endpoint : POST /api/help-chat
Auth     : None (public endpoint)
Rate Limit: 10 req/min per IP (in-memory)
SDK      : google-genai (new unified SDK — pip install google-genai)

Flow:
  1. IP rate limit check (10 req/min)
  2. Message validate
  3. Gemini Step 1 — category classify: PLATFORM_HELP | UNKNOWN
     (ANALYTICS path intentionally removed — public users ko data nahi milega)
  4a. PLATFORM_HELP → knowledge base load → sales-friendly Gemini response
  4b. UNKNOWN       → friendly fallback + contact info (no Gemini call)

Key Difference vs chatbot.py (Owner Chatbot):
  - No JWT auth — completely public
  - No ANALYTICS path — sirf platform info
  - Sales-friendly tone (prospect/visitor ke liye, not operator)
  - IP-based rate limiting (restaurant_id nahi hai)
  - Softer, more welcoming prompt
"""

import os
import time
import glob
from collections import defaultdict
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()
router = APIRouter()

# ════════════════════════════════════════════════════════
# GEMINI SETUP
# ════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

client = genai.Client(api_key=GEMINI_API_KEY)

# Same fallback order as chatbot.py
MODELS_TO_TRY = [
    "gemini-3.1-flash-lite",  # Priority 1: 15 RPM, 500 RPD — sabse zyada headroom
    "gemini-2.5-flash",       # Priority 2: Best quality, 5 RPM
    "gemini-3-flash",         # Priority 3: Latest, 5 RPM
    "gemma-4-26b",            # Priority 4: Stability fallback (Unlimited TPM)
    "gemini-3-flash-live"     # Priority 5: Emergency traffic net (Unlimited RPD)
]


# ════════════════════════════════════════════════════════
# RATE LIMITER — in-memory, per IP
# ════════════════════════════════════════════════════════

_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT  = 10   # max requests (stricter than owner chatbot)
RATE_WINDOW = 60   # seconds

def _check_rate_limit(ip: str) -> bool:
    """True = allowed, False = blocked"""
    now    = time.time()
    window = now - RATE_WINDOW
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True

def _get_client_ip(request: Request) -> str:
    """X-Forwarded-For header se real IP nikalo (proxy/nginx ke peeche ke liye)"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Pehla IP real client hota hai
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
# PROMPTS — Sales-Friendly Tone (vs Owner's Technical Tone)
# ════════════════════════════════════════════════════════

# NOTE: Yahan sirf 2 categories hain (ANALYTICS intentionally missing)
_CATEGORY_PROMPT = """\
Classify the user message into exactly ONE category:
- PLATFORM_HELP : questions about ZenTable features, AR menu, pricing, onboarding, how it works, staff management, setup, benefits
- UNKNOWN       : anything unrelated to ZenTable or restaurant management software

Reply with ONLY one word: PLATFORM_HELP or UNKNOWN
No explanation, no punctuation, nothing else.

User message: {message}"""


# Sales-friendly prompt — visitor ko convince karna hai, owner ko train nahi
_PLATFORM_HELP_PROMPT = """\
You are a friendly sales assistant for ZenTable — a modern restaurant management platform.
You are talking to potential restaurant owners and managers who are exploring the platform.

Your goal: Help them understand ZenTable's value, answer their questions clearly, and guide them toward signing up.
Answer in Hinglish (Hindi + English mix) — warm, enthusiastic, and easy to understand.

STRICT RULES:
- Answer ONLY from the knowledge base provided below
- If answer not found: say "Yeh specific detail ke liye aap hamare team se directly baat kar sakte hain: contact@zentable.in — woh aapki poori help karenge!"
- Do NOT make up features, prices, or steps
- Do NOT answer questions unrelated to ZenTable
- Keep responses concise — 2-4 sentences, unless a step-by-step explanation is needed
- End with a gentle call-to-action when relevant (e.g., "Free trial ke liye sign up kar sakte hain!")

Knowledge Base:
{knowledge}

Visitor question: {message}"""


# ════════════════════════════════════════════════════════
# GEMINI CALL (same fallback logic as chatbot.py)
# ════════════════════════════════════════════════════════

def _gemini_call(prompt: str, json_mode: bool = False) -> str:
    """Try-Except loop ke sath fallback logic aur low temperature"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json" if json_mode else "text/plain",
        temperature=0.4  # Thoda higher than owner chatbot — sales tone mein warmth chahiye
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

            if any(keyword in error_str for keyword in ["503", "429", "overloaded", "quota", "exhausted"]):
                print(f"[HelpChat Warning] {current_model} overloaded/failed. Switching to next model...")
                continue
            else:
                print(f"[HelpChat Error] Failed with {current_model}: {str(e)}. Switching just in case...")
                continue

    raise HTTPException(status_code=502, detail=f"AI service error on all models. Last error: {str(last_error)}")


def _classify_category(message: str) -> str:
    """PLATFORM_HELP | UNKNOWN return karo"""
    result = _gemini_call(_CATEGORY_PROMPT.format(message=message)).upper().strip()
    if result not in ("PLATFORM_HELP", "UNKNOWN"):
        return "UNKNOWN"
    return result


# ════════════════════════════════════════════════════════
# PATH HANDLERS
# ════════════════════════════════════════════════════════

def _handle_platform_help(message: str) -> str:
    knowledge = _load_knowledge_base()
    return _gemini_call(
        _PLATFORM_HELP_PROMPT.format(message=message, knowledge=knowledge)
    )


def _handle_unknown() -> str:
    return (
        "Yeh mere scope se thoda bahar hai 😊 "
        "Main ZenTable ke baare mein sawaalon ka jawab de sakta hoon — "
        "jaise features, AR menu, pricing, ya setup ke baare mein. "
        "Kuch aur jaanna hai? Ya seedha baat karni hai to: contact@zentable.in"
    )


def _handle_analytics_attempt() -> str:
    """
    Agar koi visitor analytics pooche (e.g. 'meri sales dikhao') —
    yeh tab call hoga jab PLATFORM_HELP classify ho lekin analytics intent detect ho.
    Abhi ke liye UNKNOWN path hi handle karega, yeh function future ke liye reserved hai.
    """
    return (
        "Sales aur analytics data sirf restaurant owners ke liye available hai — "
        "apne ZenTable dashboard mein login karke dekh sakte hain. "
        "Agar account nahi hai to sign up karo: zentable.in 🚀"
    )


# ════════════════════════════════════════════════════════
# REQUEST MODEL + ENDPOINT
# ════════════════════════════════════════════════════════

class HelpChatRequest(BaseModel):
    message: str


@router.post("/api/help-chat")
async def help_chat(
    request: Request,
    body:    HelpChatRequest,
):
    # ── 1. IP extract ──
    client_ip = _get_client_ip(request)

    # ── 2. Rate limit (IP-based, 10/min) ──
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Bahut zyada messages! Thodi der baad try karo 😊"
        )

    # ── 3. Message validate ──
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message empty hai")
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="Message bahut lamba hai (max 500 characters)")

    # ── 4. Category classify ──
    category = _classify_category(message)

    # ── 5. Path route ──
    if category == "PLATFORM_HELP":
        response_text = _handle_platform_help(message)
    else:
        response_text = _handle_unknown()

    # NOTE: category field yahan bhi return kar rahe hain debug ke liye
    # Production mein isko hata sakte hain
    return JSONResponse({
        "response": response_text,
        "category": category,
    })
