"""
glb_token.py — GLB file ke liye HMAC-signed token system

Token 10 min ke liye valid hota hai.
main.py se nikala gaya — zero internal project dependencies.
"""

import os
import hashlib
import hmac
import base64
from datetime import datetime, timezone

GLB_SECRET       = os.environ["GLB_SECRET"]
GLB_TOKEN_EXPIRY = 600  # seconds — 10 minutes


def create_glb_token(client_id: str, filepath: str) -> str:
    """
    GLB file ke liye signed token banao.
    filepath — JSON mein stored value, e.g. "clint_one/burger.glb"
    """
    expires = int(datetime.now(timezone.utc).timestamp()) + GLB_TOKEN_EXPIRY
    msg     = f"{client_id}:{filepath}:{expires}"
    sig     = hmac.new(GLB_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    payload = base64.urlsafe_b64encode(f"{msg}:{sig}".encode()).decode()
    return payload


def verify_glb_token(token: str):
    """
    Token verify karo.
    Valid hone pe (client_id, filepath) tuple return karo.
    Invalid / expired hone pe None return karo.
    """
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts   = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        msg, sig = parts
        expected = hmac.new(GLB_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        msg_parts = msg.split(":")
        if len(msg_parts) != 3:
            return None
        client_id, filepath, expires_str = msg_parts
        if int(datetime.now(timezone.utc).timestamp()) > int(expires_str):
            return None
        return client_id, filepath
    except Exception:
        return None
