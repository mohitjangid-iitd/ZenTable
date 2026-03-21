"""
auth.py — JWT authentication logic
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Cookie
from database import verify_staff, verify_admin

# ── Secret key — production mein env variable se lena ──
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM  = "HS256"

# ── Token expiry by role ──
EXPIRY = {
    "owner":   timedelta(days=7),
    "waiter":  timedelta(hours=12),
    "kitchen": timedelta(hours=12),
    "counter": timedelta(hours=12),
    "admin":   timedelta(hours=24),
}

# ── Role → redirect path ──
ROLE_REDIRECT = {
    "owner":   "/{restaurant_id}/staff/owner",
    "kitchen": "/{restaurant_id}/staff/kitchen",
    "waiter":  "/{restaurant_id}/staff/waiter",
    "counter": "/{restaurant_id}/staff/counter",
    "admin":   "/admin",
}

def create_token(payload: dict, role: str) -> str:
    """JWT token banao"""
    expire = datetime.utcnow() + EXPIRY.get(role, timedelta(hours=12))
    data = {**payload, "exp": expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """JWT token decode karo — invalid/expired hone pe None return karo"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def login_staff(restaurant_id: str, username: str, password: str):
    """
    Staff login — success pe (token, staff_dict) return karo
    Fail pe None return karo
    """
    staff = verify_staff(restaurant_id, username.lower().strip(), password)
    if not staff:
        return None, None
    token = create_token({
        "sub":           staff["username"],
        "restaurant_id": staff["restaurant_id"],
        "role":          staff["role"],
        "name":          staff["name"],
        "staff_id":      staff["id"],
    }, staff["role"])
    return token, staff

def login_admin(username: str, password: str):
    """
    Admin login — success pe (token, admin_dict) return karo
    Fail pe None return karo
    """
    admin = verify_admin(username, password)
    if not admin:
        return None, None
    token = create_token({
        "sub":      admin["username"],
        "role":     "admin",
        "name":     admin["name"],
        "admin_id": admin["id"],
    }, "admin")
    return token, admin

def get_redirect_url(role: str, restaurant_id: str = None) -> str:
    """Role ke hisaab se redirect URL banao"""
    path = ROLE_REDIRECT.get(role, "/login")
    if restaurant_id:
        path = path.replace("{restaurant_id}", restaurant_id)
    return path
