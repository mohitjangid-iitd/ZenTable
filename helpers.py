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


def get_client_data(client_id: str):
    """DB se restaurant config fetch karo — nahi mila toh None"""
    conn = get_db()
    cur  = conn.execute(
        "SELECT config FROM restaurants WHERE client_id=%s", (client_id,)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    config = row["config"]
    return config if isinstance(config, dict) else json.loads(config)


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
        if user.get("restaurant_id") != client_id:
            raise HTTPException(status_code=403, detail="Access denied — wrong restaurant")
    return user
