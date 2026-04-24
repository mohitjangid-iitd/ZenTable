"""
auth.py — JWT authentication logic
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from database import verify_staff, verify_admin, verify_owner

# ── Secret key — production mein env variable se lena ──
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM  = "HS256"

# ── Token expiry by role ──
EXPIRY = {
    "owner":   timedelta(days=7),
    "waiter":  timedelta(hours=24),
    "kitchen": timedelta(hours=24),
    "counter": timedelta(hours=24),
    "admin":   timedelta(days=7),
    "blogger": timedelta(hours=24),
}

# ── Role → redirect path ──
ROLE_REDIRECT = {
    "owner":   "/{client_id}/staff/owner",
    "kitchen": "/{client_id}/staff/kitchen",
    "waiter":  "/{client_id}/staff/waiter",
    "counter": "/{client_id}/staff/counter",
    "blogger": "/{client_id}/staff/blog",
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

def login_staff(client_id: str, username: str, password: str):
    """
    Staff login — success pe (token, staff_dict) return karo
    Fail pe None return karo
    """
    staff = verify_staff(client_id, username.lower().strip(), password)
    if not staff:
        return None, None
    token = create_token({
        "sub":       staff["username"],
        "client_id": staff["client_id"],
        "branch_id": staff.get("branch_id", "__default__"),
        "role":      staff["role"],
        "name":      staff["name"],
        "staff_id":  staff["id"],
    }, staff["role"])
    return token, staff

def login_owner(client_id: str, password: str):
    """
    Owner login (owners table) — success pe (token, owner_dict) return karo
    Fail pe None return karo
    """
    owner = verify_owner(client_id, password)
    if not owner:
        return None, None
    token = create_token({
        "sub":       owner["client_id"],
        "client_id": owner["client_id"],
        "branch_id": None,
        "role":      "owner",
        "name":      owner["name"],
        "owner_id":  owner["id"],
    }, "owner")
    return token, owner

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

def get_redirect_url(role: str, client_id: str = None) -> str:
    """Role ke hisaab se redirect URL banao"""
    path = ROLE_REDIRECT.get(role, "/login")
    if client_id:
        path = path.replace("{client_id}", client_id)
    return path
