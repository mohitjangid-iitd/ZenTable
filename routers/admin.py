"""
routers/admin.py — All admin routes

Page:
  GET  /admin
  GET  /api/admin/overview
  GET  /api/admin/summary/{client_id}
  GET  /api/admin/analytics/{client_id}

Restaurant:
  GET    /api/admin/restaurant/{client_id}/json
  PUT    /api/admin/restaurant/{client_id}/json
  POST   /api/admin/restaurant
  DELETE /api/admin/restaurant/{client_id}
  PATCH  /api/admin/restaurant/{client_id}/toggle
  GET    /api/admin/restaurant/{client_id}/analytics

Staff:
  GET    /api/admin/staff/{client_id}
  POST   /api/admin/staff/{client_id}
  PATCH  /api/admin/staff/{staff_id}/password
  PATCH  /api/admin/staff/{staff_id}/toggle
  DELETE /api/admin/staff/{staff_id}

Admin account:
  POST   /api/admin/create
  PATCH  /api/admin/password

Upload:
  POST /api/admin/upload/{client_id}
  GET  /api/admin/restaurant/{client_id}/assets-zip

Trash:
  GET    /api/admin/trash
  POST   /api/admin/trash/{trash_name}/restore
  GET    /api/admin/trash/{trash_name}/download
  DELETE /api/admin/trash/{trash_name}
  DELETE /api/admin/trash

Export:
  GET /api/admin/export/db-zip
"""

import os
import json
import bcrypt
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.background import BackgroundTask
from templates_env import templates

from database import (
    get_db,
    get_analytics, get_summary,
    get_all_restaurants_info, get_overall_stats, get_top_dishes_overall,
    save_restaurant_json, delete_restaurant_full,
    create_staff, get_staff_list, update_staff_password,
    toggle_staff_active, delete_staff,
    create_admin, export_full_db_zip,
    trash_get_all, trash_get_one,
    trash_remove, trash_remove_by_client, trash_remove_all, trash_remove_expired,
)
from helpers import get_client_data, require_auth, require_feature
from r2 import (
    USE_R2, IS_PROD, R2_BUCKET, _r2_client,
    r2_upload, r2_delete, r2_copy, r2_presign, r2_public_url,
)
from trash_utils import IST, TRASH_DIR, move_to_trash, restore_from_trash, delete_from_trash
from site_config import SITE_CONFIG

router = APIRouter()

# ── Upload config ──
UPLOAD_RULES = {
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
        "max_mb": 10,
        "folder": "static/assets",
        "url_prefix": "/static/assets",
    },
    "mind": {
        "extensions": {".mind"},
        "max_mb": 50,
        "folder": "static/assets",
        "url_prefix": "/static/assets",
        "fixed_name": "targets.mind",
    },
    "model": {
        "extensions": {".glb", ".gltf"},
        "max_mb": 100,
        "folder": "private/assets",
        "url_prefix": None,
    },
}


# ── Pydantic models ──

class SaveRestaurantRequest(BaseModel):
    data: dict

class CreateRestaurantRequest(BaseModel):
    client_id: str
    name: str
    num_tables: int = 6
    tagline: str = ""
    description: str = ""
    cuisine_type: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    lunch: str = ""
    dinner: str = ""
    closed: str = ""
    instagram: str = ""
    facebook: str = ""
    twitter: str = ""

class CreateStaffRequest(BaseModel):
    username: str
    password: str
    name: str
    role: str

class UpdatePasswordRequest(BaseModel):
    new_password: str

class CreateAdminRequest(BaseModel):
    name: str
    username: str
    password: str


# ════════════════════════════════
# ADMIN PAGE + OVERVIEW + ANALYTICS
# ════════════════════════════════

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, auth_token: Optional[str] = Cookie(None)):
    if IS_PROD and request.headers.get("host") != "admin.zentable.in":
        raise HTTPException(status_code=404)
    user = require_auth(auth_token, ["admin"])
    response = templates.TemplateResponse("admin.html", {
        "request": request, "site": SITE_CONFIG, "user": user,
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@router.get("/api/admin/overview")
async def api_admin_overview(period: str = "alltime", auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    restaurants = get_all_restaurants_info()
    for r in restaurants:
        rdata = get_client_data(r["client_id"]) or {}
        r["active"] = rdata.get("subscription", {}).get("active", True)
    return {
        "stats":      get_overall_stats(),
        "restaurants": restaurants,
        "top_dishes": get_top_dishes_overall(10, period),
    }


@router.get("/api/admin/summary/{client_id}")
async def api_summary(client_id: str):
    return get_summary(client_id)


@router.get("/api/admin/analytics/{client_id}")
async def api_analytics(client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    require_feature(data, "analytics")
    return get_analytics(client_id)


@router.get("/api/admin/restaurant/{client_id}/analytics")
async def api_admin_restaurant_analytics(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return get_analytics(client_id)


# ════════════════════════════════
# RESTAURANT CRUD
# ════════════════════════════════

@router.get("/api/admin/restaurant/{client_id}/json")
async def api_get_restaurant_json(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return data


@router.put("/api/admin/restaurant/{client_id}/json")
async def api_save_restaurant_json(client_id: str, body: SaveRestaurantRequest,
                                    auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    save_restaurant_json(client_id, body.data)
    return {"message": "Saved"}


@router.post("/api/admin/restaurant")
async def api_create_restaurant(body: CreateRestaurantRequest,
                                 auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    client_id = body.client_id.lower().replace(" ", "_")
    if get_client_data(client_id):
        raise HTTPException(status_code=409, detail="Restaurant already exists")

    data = {
        "restaurant": {
            "name": body.name, "num_tables": body.num_tables,
            "tagline": body.tagline or f"Welcome to {body.name}",
            "logo":    f"/static/assets/{client_id}/logo.png",
            "banner":  f"/static/assets/{client_id}/banner.png",
            "description": body.description, "cuisine_type": body.cuisine_type,
            "phone": body.phone, "email": body.email, "address": body.address,
            "timings": {"lunch": body.lunch, "dinner": body.dinner, "closed": body.closed},
            "social":  {"instagram": body.instagram, "facebook": body.facebook, "twitter": body.twitter},
        },
        "theme": {
            "primary_color": "#D4AF37", "secondary_color": "#1a1a1a",
            "accent_color": "#8B4513", "text_color": "#333333",
            "background": "#ffffff", "font_primary": "Playfair Display",
            "font_secondary": "Poppins",
        },
        "subscription": {"features": ["basic"]},
        "items": [],
    }

    if not USE_R2:
        os.makedirs(f"static/assets/{client_id}", exist_ok=True)
        os.makedirs(f"private/assets/{client_id}", exist_ok=True)
    else:
        data["restaurant"]["logo"]   = r2_public_url(f"{client_id}/logo.png")
        data["restaurant"]["banner"] = r2_public_url(f"{client_id}/banner.png")

    save_restaurant_json(client_id, data)
    from database import seed_tables
    seed_tables(client_id, body.num_tables)
    return {"message": f"Restaurant {client_id} created", "client_id": client_id}


@router.delete("/api/admin/restaurant/{client_id}")
async def api_delete_restaurant(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    delete_restaurant_full(client_id)

    if USE_R2:
        try:
            paginator = _r2_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=R2_BUCKET, Prefix=f"{client_id}/"):
                objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if objects:
                    _r2_client.delete_objects(Bucket=R2_BUCKET, Delete={"Objects": objects})
        except Exception:
            pass
    else:
        for assets_dir in [f"static/assets/{client_id}", f"private/assets/{client_id}"]:
            if os.path.exists(assets_dir):
                shutil.rmtree(assets_dir, ignore_errors=True)

    return {"message": f"Restaurant {client_id} deleted"}


@router.patch("/api/admin/restaurant/{client_id}/toggle")
async def api_toggle_restaurant(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    current   = data.get("subscription", {}).get("active", True)
    new_state = not current
    if "subscription" not in data:
        data["subscription"] = {"features": ["basic"]}
    data["subscription"]["active"] = new_state
    save_restaurant_json(client_id, data)
    return {"active": new_state}


# ════════════════════════════════
# STAFF MANAGEMENT
# ════════════════════════════════

@router.get("/api/admin/staff/{client_id}")
async def api_admin_get_staff(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    return get_staff_list(client_id)


@router.post("/api/admin/staff/{client_id}")
async def api_admin_create_staff(client_id: str, body: CreateStaffRequest,
                                  auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    valid_roles = {"owner", "kitchen", "waiter", "counter"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    ok = create_staff(client_id, body.username, body.password, body.name, body.role)
    if not ok:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": "Staff created"}


@router.patch("/api/admin/staff/{staff_id}/password")
async def api_admin_update_password(staff_id: int, body: UpdatePasswordRequest,
                                     auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    update_staff_password(staff_id, body.new_password)
    return {"message": "Password updated"}


@router.patch("/api/admin/staff/{staff_id}/toggle")
async def api_admin_toggle_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    conn = get_db()
    row  = conn.execute("SELECT is_active FROM staff WHERE id=%s", (staff_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    new_state = not bool(row[0])
    toggle_staff_active(staff_id, new_state)
    return {"message": "Updated", "is_active": new_state}


@router.delete("/api/admin/staff/{staff_id}")
async def api_admin_delete_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    delete_staff(staff_id)
    return {"message": "Staff deleted"}


# ════════════════════════════════
# ADMIN ACCOUNT
# ════════════════════════════════

@router.post("/api/admin/create")
async def api_create_admin(body: CreateAdminRequest, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not body.name or not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Sab fields required hain")
    ok = create_admin(body.username, body.password, body.name)
    if not ok:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": f"Admin '{body.name}' created"}


@router.patch("/api/admin/password")
async def api_admin_change_own_password(body: UpdatePasswordRequest,
                                         auth_token: Optional[str] = Cookie(None)):
    user          = require_auth(auth_token, ["admin"])
    if not body.new_password:
        raise HTTPException(status_code=400, detail="Password required")
    password_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    conn.execute("UPDATE admins SET password_hash=%s WHERE id=%s",
                 (password_hash, user["admin_id"]))
    conn.commit()
    conn.close()
    return {"message": "Password updated"}


# ════════════════════════════════
# UPLOAD
# ════════════════════════════════

@router.post("/api/admin/upload/{client_id}")
async def api_upload_asset(
    client_id: str,
    file: UploadFile = File(...),
    type: str = Form(...),
    old_path: Optional[str] = Form(None),
    auth_token: Optional[str] = Cookie(None),
):
    require_auth(auth_token, ["admin"])

    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if type not in UPLOAD_RULES:
        raise HTTPException(status_code=400, detail=f"type must be: {', '.join(UPLOAD_RULES)}")

    rule          = UPLOAD_RULES[type]
    original_name = file.filename or "upload"
    ext           = os.path.splitext(original_name)[1].lower()

    if ext not in rule["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"'{ext}' allowed nahi. Allowed: {', '.join(rule['extensions'])}"
        )

    contents  = await file.read()
    max_bytes = rule["max_mb"] * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File bahut badi hai. Max {rule['max_mb']}MB allowed."
        )

    safe_name = rule.get("fixed_name") or os.path.basename(original_name).replace(" ", "_")
    folder    = os.path.join(rule["folder"], client_id)
    if not USE_R2:
        os.makedirs(folder, exist_ok=True)

    save_path = os.path.join(folder, safe_name)
    r2_key    = f"{client_id}/{safe_name}"

    # ── Purani file trash mein move karo (mind except) ──
    if type != "mind":
        trash_target = r2_key if USE_R2 else save_path
        move_to_trash(client_id, trash_target, type)

        if old_path and old_path.strip().lower() not in ("", "none"):
            old_path = old_path.strip().lstrip("/")
            if USE_R2:
                old_key = old_path
                for prefix in ("static/assets/", "private/assets/"):
                    if old_path.startswith(prefix):
                        old_key = old_path[len(prefix):]
                        break
                if old_key != r2_key:
                    move_to_trash(client_id, old_key, type)
            else:
                old_full = os.path.join("private/assets", old_path) if type == "model" \
                           else old_path
                if os.path.abspath(old_full) != os.path.abspath(save_path):
                    move_to_trash(client_id, old_full, type)

    # ── File save ──
    if USE_R2:
        r2_upload(contents, f"{client_id}/{safe_name}", safe_name)
    else:
        with open(save_path, "wb") as f:
            f.write(contents)

    # ── GLB optimization ──
    audit_data = None
    result     = {}
    if type == "model":
        try:
            from glb_optimizer import optimize_and_audit
            with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tmp:
                tmp_out = tmp.name
            success, result = optimize_and_audit(save_path, tmp_out)
            if success and os.path.exists(tmp_out):
                shutil.move(tmp_out, save_path)
            audit_data = result.get("audit")
        except Exception:
            pass

    # ── Return path ──
    if USE_R2:
        path = f"{client_id}/{safe_name}" if type == "model" \
               else r2_public_url(f"{client_id}/{safe_name}")
    else:
        path = f"{rule['url_prefix']}/{client_id}/{safe_name}" if rule["url_prefix"] \
               else f"{client_id}/{safe_name}"

    return JSONResponse({
        "path": path,
        "filename": safe_name,
        "audit": audit_data,
        "optimization_message": result.get("message", "") if audit_data else "",
    })


@router.get("/api/admin/restaurant/{client_id}/assets-zip")
async def api_download_assets_zip(
    client_id: str,
    folder: str,
    auth_token: Optional[str] = Cookie(None),
):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if folder == "static":
        assets_dir = f"static/assets/{client_id}"
        zip_name   = f"{client_id}_assets.zip"
    elif folder == "private":
        assets_dir = f"private/assets/{client_id}"
        zip_name   = f"{client_id}_models.zip"
    else:
        raise HTTPException(status_code=400, detail="folder must be 'static' or 'private'")

    if not os.path.exists(assets_dir) or not os.listdir(assets_dir):
        raise HTTPException(status_code=404, detail="No assets found")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname  = os.path.relpath(filepath, assets_dir)
                zf.write(filepath, arcname)
    tmp.close()

    return FileResponse(tmp.name, media_type="application/zip", filename=zip_name)


# ════════════════════════════════
# TRASH
# ════════════════════════════════

@router.get("/api/admin/trash")
async def api_get_trash(client_id: str = None, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    entries = trash_get_all(client_id)
    now     = datetime.now(IST)
    result  = []
    for entry in entries:
        try:
            from datetime import timezone, timedelta
            expiry    = datetime.strptime(entry["auto_delete_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
            days_left = max(0, (expiry - now).days)
        except Exception:
            days_left = None
        result.append({**entry, "days_left": days_left})
    return result


@router.post("/api/admin/trash/{trash_name}/restore")
async def api_restore_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    ok = restore_from_trash(trash_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila ya file missing hai")
    return {"message": f"'{trash_name}' restore ho gayi"}


@router.get("/api/admin/trash/{trash_name}/download")
async def api_download_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    entry = trash_get_one(trash_name)
    if not entry:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila")

    if entry.get("storage") == "r2" or USE_R2:
        presigned = r2_presign(f"trash/{entry['client_id']}/{trash_name}", expires=300)
        return RedirectResponse(url=presigned, status_code=302)

    trash_path = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
    if not os.path.exists(trash_path):
        raise HTTPException(status_code=404, detail="File disk pe nahi mili")
    return FileResponse(trash_path, filename=entry["original_name"],
                        media_type="application/octet-stream")


@router.delete("/api/admin/trash/{trash_name}")
async def api_delete_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    ok = delete_from_trash(trash_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila")
    return {"message": f"'{trash_name}' permanently delete ho gayi"}


@router.delete("/api/admin/trash")
async def api_empty_trash(client_id: str = None, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    entries = trash_get_all(client_id)
    removed = 0
    for entry in entries:
        try:
            if entry.get("storage") == "r2" or USE_R2:
                r2_delete(f"trash/{entry['client_id']}/{entry['trash_name']}")
            else:
                trash_path = os.path.join(TRASH_DIR, entry["client_id"], entry["trash_name"])
                if os.path.exists(trash_path):
                    os.remove(trash_path)
        except Exception:
            pass
        removed += 1

    if client_id:
        trash_remove_by_client(client_id)
    else:
        trash_remove_all()

    return {"message": f"{removed} file(s) permanently delete ki gayi"}


# ════════════════════════════════
# EXPORT
# ════════════════════════════════

@router.get("/api/admin/export/db-zip")
async def api_export_db_zip(auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    zip_path = export_full_db_zip()
    filename = f"zentable_db_{datetime.now(IST).strftime('%d-%m-%Y_%H-%M')}_IST.zip"
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(os.remove, zip_path),
    )
