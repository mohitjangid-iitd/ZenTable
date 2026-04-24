"""
helpers.py — Shared helper functions for route handlers

get_client_data, require_auth, require_feature etc.
main.py se nikala gaya — saare routers yahan se import karenge.
"""

import json
from typing import Optional
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from database import get_db
from auth import decode_token, get_redirect_url
from site_config import SITE_CONFIG


def get_client_data(client_id: str, branch_id: str = "__default__"):
    """
    DB se restaurant config fetch karo.
    - branch ka config return karta hai
    - theme brand-level se merge hoti hai (sirf __default__ row pe hoti hai)
    - nahi mila toh None
    """
    conn = get_db()

    # Branch-level config
    cur = conn.execute(
        "SELECT config, theme FROM restaurants WHERE client_id=%s AND branch_id=%s",
        (client_id, branch_id)
    )
    row = cur.fetchone()

    # Agar specific branch nahi mili aur __default__ nahi maanga tha
    # toh __default__ try karo (fallback)
    if not row and branch_id != "__default__":
        cur = conn.execute(
            "SELECT config, theme FROM restaurants WHERE client_id=%s AND branch_id='__default__'",
            (client_id,)
        )
        row = cur.fetchone()

    conn.close()
    if not row:
        return None

    config = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])

    # Theme merge karo — brand-level shared hai
    theme = row["theme"]
    if theme:
        config["theme"] = theme if isinstance(theme, dict) else json.loads(theme)
    elif "theme" not in config:
        # Theme alag row pe stored hai — fetch karo
        conn2 = get_db()
        cur2 = conn2.execute(
            "SELECT theme FROM restaurants WHERE client_id=%s AND theme IS NOT NULL LIMIT 1",
            (client_id,)
        )
        trow = cur2.fetchone()
        conn2.close()
        if trow and trow["theme"]:
            config["theme"] = trow["theme"] if isinstance(trow["theme"], dict) else json.loads(trow["theme"])

    return config


def has_feature(data: dict, feature: str) -> bool:
    """Restaurant ke liye feature enabled hai ya nahi"""
    features = data.get("subscription", {}).get("features", ["basic"])
    return feature in features


def require_feature(data: dict, feature: str):
    """Feature nahi hai toh 403"""
    if not has_feature(data, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' not available")


def is_restaurant_active(data: dict) -> bool:
    return data.get("subscription", {}).get("active", True)


def closed_response(request, data, client_id):
    return RedirectResponse(url=SITE_CONFIG["instagram"], status_code=302)


def get_current_user(token: Optional[str]) -> Optional[dict]:
    """Cookie token decode karo"""
    if not token:
        return None
    return decode_token(token)


def require_auth(token: Optional[str], allowed_roles: list, client_id: str = None) -> dict:
    """
    Auth check — fail hone pe 302 login redirect.
    client_id dene pe restaurant match bhi check hoga (admin exempt).
    Returns user dict with branch_id guaranteed present.
    """
    user = get_current_user(token)
    if not user:
        login_url = "/admin/login" if allowed_roles == ["admin"] else "/login"
        raise HTTPException(
            status_code=302,
            headers={
                "Location": login_url,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            }
        )
    if user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    if client_id and user.get("role") != "admin":
        # client_id token mein client_id ya legacy restaurant_id key mein ho sakta hai
        user_cid = user.get("client_id") or user.get("restaurant_id")
        if user_cid != client_id:
            raise HTTPException(status_code=403, detail="Access denied — wrong restaurant")

    # branch_id guaranteed hona chahiye — owner ke liye None (all branches)
    if "branch_id" not in user:
        user["branch_id"] = None if user.get("role") == "owner" else "__default__"

    return user
