"""
routers/image_to_menu.py — Image to Menu Extraction
=====================================================
Endpoints:
  POST /api/admin/image-to-menu/{client_id}   → Admin (any restaurant)
  POST /api/owner/{client_id}/image-to-menu   → Owner (sirf apna restaurant)

Auth  : JWT cookie
Model : gemini-2.5-flash (vision-capable, multimodal)

Flow:
  1. JWT verify + role check
  2. Owner → client_id ownership verify
  3. Image validate + base64 encode
  4. Gemini vision → JSON dishes array extract
  5. Validate + return dishes
"""

import os
import json
import base64
from fastapi import APIRouter, HTTPException, Cookie, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
from dotenv import load_dotenv

from google import genai
from google.genai import types

from auth import decode_token

load_dotenv()
router = APIRouter()

# ════════════════════════════════════════════════════════
# GEMINI SETUP
# ════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

client = genai.Client(api_key=GEMINI_API_KEY)

# Vision-capable models ka priority list — same pattern as chatbot.py
# Sirf woh models jo image input support karte hain (Gemma/text-only models yahan kaam nahi karenge)
VISION_MODELS_TO_TRY = [
    "gemini-2.5-flash",          # Priority 1: Best quality vision, 5 RPM free
    "gemini-3.1-flash",          # Priority 2: 5 RPM free, multimodal
    "gemini-3-flash",            # Priority 3: 5 RPM free, fallback
]

# Max image size: 10MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg":  "image/jpeg",
    "image/png":  "image/png",
    "image/webp": "image/webp",
}

# ════════════════════════════════════════════════════════
# EXTRACTION PROMPT
# ════════════════════════════════════════════════════════

IMAGE_TO_MENU_PROMPT = """You are a menu extraction assistant for an Indian restaurant app.

TASK: Extract every dish from the menu image into a JSON array.
OUTPUT: Return ONLY the raw JSON array. No explanation. No markdown. Start with [ and end with ].

---

SCHEMA for each dish:
{
  "veg": boolean,
  "name": "exact name as on menu",
  "category": "exact section heading from menu",
  "price": "INR 120",
  "description": "",
  "ingredients": ""
}

---

SIZES RULE — when a dish shows two or more prices (e.g. ₹129/₹159):
Look at the section heading and dish context to determine the correct labels:
- "Gravy / Dry" section → labels are "Gravy" and "Dry"
- "Small/Medium/Large" context → use those labels
- "(Veg/Egg/Chicken)" written next to the dish name → three sizes with labels "Veg", "Egg", "Chicken"

When using sizes, REMOVE the price field entirely:
{
  "name": "Schezwan Noodles",
  "category": "Noodles",
  "veg": false,
  "sizes": [{"label": "Veg", "price": "129"}, {"label": "Non-Veg", "price": "159"}],
  "description": "",
  "ingredients": ""
}

---

SPLIT RULE — some dishes must be split into separate objects:

1. If a dish name contains both a veg and non-veg option (e.g. "Chilli Paneer/Chicken"):
   → Create TWO separate dish objects, one for each variant.
   → Set veg correctly for each.

2. If a section heading contains "V/NV" or "Veg/Non-Veg" (e.g. "PASTA : V/NV"):
   → Every dish in that section must be split into TWO separate objects.
   → One with "(Veg)" appended to the name and veg: true.
   → One with "(Non-Veg)" appended to the name and veg: false.
   → Each gets its own price, NOT a sizes array.
   Example:
   "Red Sauce Pasta" at ₹179/₹209 in "PASTA : V/NV" section becomes:
   {"veg": true, "name": "Red Sauce Pasta (Veg)", "category": "Pasta", "price": "INR 179", ...}
   {"veg": false, "name": "Red Sauce Pasta (Non-Veg)", "category": "Pasta", "price": "INR 209", ...}

---

VEG DETECTION RULES:
- veg: false → if name contains chicken, mutton, egg, fish, prawn, or any non-veg ingredient
- veg: true → if name contains paneer, corn, veg, or is clearly vegetarian
- When in doubt → veg: false

---

GENERAL RULES:
- Do not skip any dish visible in the image.
- Do not invent or assume dishes not shown.
- Use the exact section heading from the menu as the category value.
- price format must always be "INR <amount>" (e.g. "INR 149").
- Leave description and ingredients as empty strings "" unless clearly mentioned on the menu."""


# ════════════════════════════════════════════════════════
# GEMINI VISION CALL
# ════════════════════════════════════════════════════════

def _extract_dishes_from_image(image_bytes: bytes, mime_type: str) -> list:
    """Image bytes se dishes extract karo using Gemini vision"""

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    image_part = types.Part.from_bytes(
        data=base64.b64decode(image_b64),
        mime_type=mime_type,
    )
    text_part = types.Part.from_text(text=IMAGE_TO_MENU_PROMPT)

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,  # Low temperature — factual extraction, no hallucination
    )

    last_error = None
    for model in VISION_MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[image_part, text_part],
                config=config,
            )
            raw = response.text.strip()

            # Clean up any stray markdown if model ignores mime type
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

            dishes = json.loads(raw)
            if not isinstance(dishes, list):
                raise ValueError("Response is not a JSON array")

            return dishes

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {str(e)}"
            continue
        except Exception as e:
            last_error = str(e)
            error_lower = str(e).lower()
            if "429" in error_lower or "quota" in error_lower or "resource_exhausted" in error_lower:
                raise HTTPException(
                    status_code=503,
                    detail="Image scan nahi ho saki. Thodi der baad try karo."
                )
            if any(k in error_lower for k in ["503", "overloaded"]):
                continue
            continue

    raise HTTPException(
        status_code=502,
        detail="Image scan nahi ho saki. Thodi der baad try karo."
    )


# ════════════════════════════════════════════════════════
# SHARED HANDLER — dono endpoints yahi call karte hain
# ════════════════════════════════════════════════════════

async def _handle_image_to_menu(image: UploadFile) -> JSONResponse:
    """Image validate karo aur dishes extract karo — common logic"""

    # ── Image type validate ──
    content_type = (image.content_type or "").lower()
    mime_type = ALLOWED_MIME_TYPES.get(content_type)
    if not mime_type:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. JPG, PNG, or WebP upload karo."
        )

    image_bytes = await image.read()

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file upload hua")

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image bahut badi hai (max 10MB)"
        )

    # ── Gemini vision extraction ──
    try:
        dishes = _extract_dishes_from_image(image_bytes, mime_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # ── Empty result ──
    if not dishes:
        return JSONResponse({
            "success": False,
            "message": "Koi dish nahi mili. Clearer photo try karo ya ensure karo menu clearly visible ho.",
            "dishes": [],
            "count": 0,
        })

    return JSONResponse({
        "success": True,
        "dishes": dishes,
        "count": len(dishes),
    })


# ════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════

@router.post("/api/admin/image-to-menu/{client_id}")
async def admin_image_to_menu(
    client_id:  str,
    image:      UploadFile = File(...),
    auth_token: Optional[str] = Cookie(default=None),
):
    """Admin endpoint — kisi bhi restaurant ka menu scan kar sakta hai"""
    # ── 1. JWT verify ──
    if not auth_token:
        raise HTTPException(status_code=401, detail="Login required")

    payload = decode_token(auth_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # ── 2. Sirf admin ──
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can use this endpoint")

    # ── 3. Extract ──
    return await _handle_image_to_menu(image)


@router.post("/api/owner/{client_id}/image-to-menu")
async def owner_image_to_menu(
    client_id:  str,
    image:      UploadFile = File(...),
    auth_token: Optional[str] = Cookie(default=None),
):
    """Owner endpoint — sirf apne restaurant ka menu scan kar sakta hai"""
    # ── 1. JWT verify ──
    if not auth_token:
        raise HTTPException(status_code=401, detail="Login required")

    payload = decode_token(auth_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # ── 2. Sirf owner ──
    if payload.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only restaurant owners can use this endpoint")

    # ── 3. Ownership verify — owner sirf apna restaurant access kar sake ──
    if payload.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Aap sirf apne restaurant ka menu scan kar sakte ho")

    # ── 4. Extract ──
    return await _handle_image_to_menu(image)
