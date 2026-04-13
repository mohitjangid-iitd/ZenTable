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

from auth import login_staff, login_admin, get_redirect_url
from helpers import get_client_data, get_current_user
from r2 import IS_PROD
from site_config import SITE_CONFIG

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    restaurant_id: Optional[str] = None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if user and user.get("role") != "admin":
        redirect_url = get_redirect_url(user["role"], user.get("restaurant_id"))
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


@router.post("/api/auth/login")
async def api_login(body: LoginRequest, response: Response):
    if body.restaurant_id:
        rdata = get_client_data(body.restaurant_id)
        if rdata and not rdata.get("subscription", {}).get("active", True):
            raise HTTPException(
                status_code=403,
                detail="Subscription expired. Please contact your administrator."
            )
        token, user = login_staff(body.restaurant_id, body.username, body.password)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        redirect_url = get_redirect_url(user["role"], user["restaurant_id"])
    else:
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
