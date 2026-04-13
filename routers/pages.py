"""
routers/pages.py — Public + Staff HTML page routes

Public:
  GET /{client_id}
  GET /{client_id}/menu
  GET /{client_id}/ar-menu
  GET /{client_id}/table/{table_no}
  GET /{client_id}/table/{table_no}/menu
  GET /{client_id}/table/{table_no}/ar-menu

Staff (auth required):
  GET /{client_id}/staff/owner
  GET /{client_id}/staff/kitchen
  GET /{client_id}/staff/waiter
  GET /{client_id}/staff/counter

Admin:
  GET /admin
  GET /api/admin/summary/{client_id}
  GET /api/admin/analytics/{client_id}
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request

from database import get_table_status, get_summary, get_analytics
from helpers import (
    get_client_data, require_auth,
    is_restaurant_active, closed_response, require_feature,
)
from r2 import USE_R2, IS_PROD, r2_public_url
from site_config import SITE_CONFIG
from templates_env import templates

router = APIRouter()
def _block_on_admin_subdomain(request: Request):
    if IS_PROD and request.headers.get("host") == "admin.zentable.in":
        raise HTTPException(status_code=404)

# ════════════════════════════════
# PUBLIC PAGES
# ════════════════════════════════

@router.get("/{client_id}", response_class=HTMLResponse)
async def restaurant_home(request: Request, client_id: str):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"]),
    })


@router.get("/{client_id}/menu", response_class=HTMLResponse)
async def menu(request: Request, client_id: str):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"]),
    })


@router.get("/{client_id}/ar-menu", response_class=HTMLResponse)
async def ar_menu(request: Request, client_id: str):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    features = data.get("subscription", {}).get("features", [])
    if "ar_menu" not in features:
        return RedirectResponse(url=f"/{client_id}/menu")
    mind_url = r2_public_url(f"{client_id}/targets.mind") if USE_R2 \
               else f"/static/assets/{client_id}/targets.mind"
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, "client_id": client_id, "table_no": None,
        "mind_url": mind_url,
    })


@router.get("/{client_id}/table/{table_no}", response_class=HTMLResponse)
async def table_home(request: Request, client_id: str, table_no: int):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active. Please ask staff.")
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": table_no,
    })


@router.get("/{client_id}/table/{table_no}/menu", response_class=HTMLResponse)
async def table_menu(request: Request, client_id: str, table_no: int):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active. Please ask staff.")
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": table_no,
        "features": data.get("subscription", {}).get("features", ["basic"]),
    })


@router.get("/{client_id}/table/{table_no}/ar-menu", response_class=HTMLResponse)
async def table_ar_menu(request: Request, client_id: str, table_no: int):
    _block_on_admin_subdomain(request)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    features = data.get("subscription", {}).get("features", [])
    if "ar_menu" not in features:
        return RedirectResponse(url=f"/{client_id}/table/{table_no}/menu")
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active. Please ask staff.")
    mind_url = r2_public_url(f"{client_id}/targets.mind") if USE_R2 \
               else f"/static/assets/{client_id}/targets.mind"
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, "client_id": client_id, "table_no": table_no,
        "mind_url": mind_url,
    })


# ════════════════════════════════
# STAFF PAGES
# ════════════════════════════════

@router.get("/{client_id}/staff/owner", response_class=HTMLResponse)
async def staff_owner(request: Request, client_id: str,
                      auth_token: Optional[str] = Cookie(None)):
    _block_on_admin_subdomain(request)
    user = require_auth(auth_token, ["owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_owner.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
        "features": data.get("subscription", {}).get("features", ["basic"]),
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/{client_id}/staff/kitchen", response_class=HTMLResponse)
async def staff_kitchen(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    _block_on_admin_subdomain(request)
    user = require_auth(auth_token, ["kitchen", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_kitchen.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/{client_id}/staff/waiter", response_class=HTMLResponse)
async def staff_waiter(request: Request, client_id: str,
                       auth_token: Optional[str] = Cookie(None)):
    _block_on_admin_subdomain(request)
    user = require_auth(auth_token, ["waiter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_waiter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/{client_id}/staff/counter", response_class=HTMLResponse)
async def staff_counter(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    _block_on_admin_subdomain(request)
    user = require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_counter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response
