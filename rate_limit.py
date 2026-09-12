"""
rate_limit.py — slowapi based rate limiting for ZenTable

Key strategy (mix):
  - Staff/owner/admin routes (JWT cookie present) → limited per user
        key = "{restaurant_id}:{staff_id}"  (or "admin:{admin_id}" for admins)
  - Customer-facing routes (no JWT — table ordering, menu, waiter call) → limited per IP

Usage in main.py:
    from rate_limit import limiter, rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

Usage in routers (per-route override):
    from rate_limit import limiter

    @router.post("/api/order/{client_id}/{table_no}")
    @limiter.limit("10/minute")
    async def place_order(request: Request, ...):
        ...

NOTE: every route decorated with @limiter.limit(...) MUST have `request: Request`
as a parameter — slowapi reads client info off the Request object.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth import decode_token


def rate_limit_key(request: Request) -> str:
    """
    Mixed key function:
      - If a valid auth_token cookie is present → key by identity (staff/admin).
      - Else → key by IP address (customer-facing routes).
    """
    token = request.cookies.get("auth_token")
    if token:
        payload = decode_token(token)
        if payload:
            role = payload.get("role")
            if role == "admin":
                admin_id = payload.get("admin_id", "unknown")
                return f"admin:{admin_id}"
            restaurant_id = payload.get("restaurant_id", "unknown")
            staff_id = payload.get("staff_id", "unknown")
            return f"staff:{restaurant_id}:{staff_id}"
    # No valid token → fall back to IP (covers customers ordering from tables)
    return f"ip:{get_remote_address(request)}"


# ── Global limiter instance ──
# Default limit applies to every route unless overridden with @limiter.limit(...)
# or explicitly exempted with @limiter.exempt.
limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=["200/minute"],   # global safety net
    headers_enabled=False,           # disabled so endpoints returning dicts don't crash
    swallow_errors=True,             # if limiter backend fails, don't 500 the app
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom JSON response instead of slowapi's default plain text."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Too many requests. Try again shortly. ({exc.detail})",
        },
    )
