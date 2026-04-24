"""
routers/auth.py — Login / Logout routes

GET  /login
GET  /admin/login
POST /api/auth/login
POST /api/auth/logout
GET  /logout
"""

from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi import Request
from pydantic import BaseModel
from templates_env import templates

from auth import login_staff, login_admin, login_owner, get_redirect_url
from helpers import get_client_data, get_current_user
from r2 import IS_PROD
from site_config import SITE_CONFIG
from database import create_signup_request

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    client_id: Optional[str] = None

class SignupRequest(BaseModel):
    name: str
    phone: str
    email: str
    restaurant_name: str
    comment: Optional[str] = None

def _send_confirmation_email(to_email: str, name: str, restaurant_name: str):
    """Owner ko confirmation email bhejo — background mein fire-and-forget"""
    import smtplib, os
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    if not smtp_user or not smtp_pass:
        print("⚠️  SMTP credentials missing — email not sent")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "ZenTable — Aapka request receive hua! 🎉"
        msg["From"]    = f"ZenTable <{smtp_user}>"
        msg["To"]      = to_email

        body = f"""Namaste {name}!

Aapne {restaurant_name} ke liye ZenTable pe signup karne ki request di hai.

Hamare executives aapse jald hi sampark karenge aur aapka account setup karenge.

Agar koi sawaal ho toh reply kar sakte hain is email pe.

Shukriya,
ZenTable Team
zentable.in
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        print(f"✅ Confirmation email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email send failed: {e}")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if user and user.get("role") != "admin":
        redirect_url = get_redirect_url(user["role"], user.get("client_id"))
        return RedirectResponse(url=redirect_url)
    return templates.TemplateResponse("login.html", {"request": request, "site": SITE_CONFIG})


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    if IS_PROD and request.headers.get("host") != "admin.zentable.in":
        raise HTTPException(status_code=404)
    user = get_current_user(auth_token)
    if user and user.get("role") == "admin":
        return RedirectResponse(url="/admin")
    return templates.TemplateResponse("admin_login.html", {"request": request, "site": SITE_CONFIG})

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    """Owner signup request form"""
    user = get_current_user(auth_token)
    if user:
        # Already logged in — apne dashboard pe bhejo
        redirect_url = get_redirect_url(user["role"], user.get("client_id"))
        return RedirectResponse(url=redirect_url)
    return templates.TemplateResponse("signup.html", {"request": request, "site": SITE_CONFIG})


@router.post("/api/auth/signup")
async def api_signup(body: SignupRequest):
    """
    Owner signup request submit karo.
    1. DB mein pending request save karo
    2. Owner ko confirmation email bhejo
    3. Admin panel pe request dikhegi
    """
    import threading

    # Basic validation
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=422, detail="Valid email required")
    if not body.phone or len(body.phone.strip()) < 10:
        raise HTTPException(status_code=422, detail="Valid phone number required")

    # DB mein save karo
    req_id = create_signup_request(
        name            = body.name.strip(),
        phone           = body.phone.strip(),
        email           = body.email.strip().lower(),
        restaurant_name = body.restaurant_name.strip(),
        comment         = body.comment.strip() if body.comment else None,
    )

    # Email fire-and-forget (thread mein — response block na ho)
    t = threading.Thread(
        target=_send_confirmation_email,
        args=(body.email.strip().lower(), body.name.strip(), body.restaurant_name.strip()),
        daemon=True
    )
    t.start()

    return {
        "success": True,
        "message": "Aapka request receive hua! Hamare executives jald hi sampark karenge.",
        "request_id": req_id,
    }

@router.post("/api/auth/login")
async def api_login(body: LoginRequest, response: Response):
    if body.client_id:
        # ── Staff login (waiter / kitchen / counter) ──
        rdata = get_client_data(body.client_id)
        if rdata and not rdata.get("subscription", {}).get("active", True):
            raise HTTPException(
                status_code=403,
                detail="Subscription expired. Please contact your administrator."
            )
        token, user = login_staff(body.client_id, body.username, body.password)

        # Staff login fail — owner table try karo (owner bhi client_id se login karta hai)
        if not token:
            token, user = login_owner(body.client_id, body.password)

        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        redirect_url = get_redirect_url(user["role"], user.get("client_id") or user.get("client_id"))
    else:
        # ── Admin login ──
        token, user = login_admin(body.username, body.password)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        redirect_url = get_redirect_url("admin")

    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=IS_PROD,
        max_age=60 * 60 * 24 * 7,
        domain=".zentable.in" if IS_PROD else None,
    )
    return {"redirect": redirect_url, "role": user["role"], "name": user["name"]}


@router.post("/api/auth/logout")
async def api_logout(request: Request, response: Response):
    response.delete_cookie("auth_token", domain=".zentable.in" if IS_PROD else None)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    is_admin = IS_PROD and request.headers.get("host") == "admin.zentable.in"
    return {"redirect": "/" if is_admin else "/login"}


@router.get("/logout")
async def logout_redirect(response: Response):
    response.delete_cookie("auth_token", domain=".zentable.in" if IS_PROD else None)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return RedirectResponse(url="/login")
