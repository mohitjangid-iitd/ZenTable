"""
routers/owner.py — Owner panel routes

Restaurant JSON:
  GET  /api/owner/{client_id}/json
  PUT  /api/owner/{client_id}/json

Staff:
  GET    /api/staff/{client_id}
  POST   /api/staff/{client_id}
  PATCH  /api/staff/{client_id}/{staff_id}/password
  PATCH  /api/staff/{client_id}/{staff_id}/toggle
  DELETE /api/staff/{client_id}/{staff_id}

Upload:
  POST /api/owner/upload/{client_id}
"""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import (
    get_db,
    get_staff_list,
    create_staff,
    update_staff_password,
    toggle_staff_active,
    delete_staff,
    save_restaurant_json,
    seed_tables,
)
from helpers import require_auth, get_client_data
from r2 import USE_R2, r2_upload, r2_public_url
from trash_utils import move_to_trash

router = APIRouter()


# ── Upload config — owner sirf images upload kar sakta hai ──
OWNER_UPLOAD_RULES = {
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
        "max_mb": 10,
        "folder": "static/assets",
        "url_prefix": "/static/assets",
    },
}


# ── Pydantic models ──

class SaveRestaurantRequest(BaseModel):
    data: dict

class CreateStaffRequest(BaseModel):
    username: str
    password: str
    name: str
    role: str

class UpdatePasswordRequest(BaseModel):
    new_password: str


# ════════════════════════════════
# RESTAURANT JSON
# ════════════════════════════════

@router.get("/api/owner/{client_id}/json")
async def owner_get_json(client_id: str, auth_token: Optional[str] = Cookie(None)):
    """Owner apna restaurant config padh sake"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return data


@router.put("/api/owner/{client_id}/json")
async def owner_save_json(client_id: str, body: SaveRestaurantRequest,
                           auth_token: Optional[str] = Cookie(None)):
    """Owner apna restaurant config save kare — theme/subscription protected"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    existing = get_client_data(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    data = body.data
    # Owner theme aur subscription nahi badal sakta
    data["subscription"] = existing.get("subscription", {})
    data["theme"]        = existing.get("theme", {})
    save_restaurant_json(client_id, data)
    # Table count change hone par seed_tables call karo
    num = data.get("restaurant", {}).get("num_tables")
    if num and isinstance(num, int) and 1 <= num <= 500:
        seed_tables(client_id, num)
    return {"ok": True}


# ════════════════════════════════
# STAFF MANAGEMENT
# ════════════════════════════════

@router.get("/api/staff/{client_id}")
async def owner_get_staff(client_id: str, auth_token: Optional[str] = Cookie(None)):
    """Apne restaurant ki staff list"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    return get_staff_list(client_id)


@router.post("/api/staff/{client_id}")
async def owner_create_staff(client_id: str, body: CreateStaffRequest,
                              auth_token: Optional[str] = Cookie(None)):
    """Naya staff member add karo"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    valid_roles = {"kitchen", "waiter", "counter"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role. Allowed: kitchen, waiter, counter")
    ok = create_staff(client_id, body.username, body.password, body.name, body.role)
    if not ok:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": "Staff created"}


@router.patch("/api/staff/{client_id}/{staff_id}/password")
async def owner_update_password(client_id: str, staff_id: int, body: UpdatePasswordRequest,
                                 auth_token: Optional[str] = Cookie(None)):
    """Staff ka password change karo"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    if not body.new_password:
        raise HTTPException(status_code=400, detail="Password required")
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM staff WHERE id=%s AND client_id=%s", (staff_id, client_id)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    update_staff_password(staff_id, body.new_password)
    return {"message": "Password updated"}


@router.patch("/api/staff/{client_id}/{staff_id}/toggle")
async def owner_toggle_staff(client_id: str, staff_id: int,
                              auth_token: Optional[str] = Cookie(None)):
    """Staff ko activate/deactivate karo"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    conn = get_db()
    row = conn.execute(
        "SELECT is_active FROM staff WHERE id=%s AND client_id=%s", (staff_id, client_id)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    new_state = not bool(row[0])
    toggle_staff_active(staff_id, new_state)
    return {"message": "Updated", "is_active": new_state}


@router.delete("/api/staff/{client_id}/{staff_id}")
async def owner_delete_staff(client_id: str, staff_id: int,
                              auth_token: Optional[str] = Cookie(None)):
    """Staff member delete karo"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM staff WHERE id=%s AND client_id=%s", (staff_id, client_id)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    delete_staff(staff_id)
    return {"message": "Staff deleted"}


# ════════════════════════════════
# UPLOAD
# ════════════════════════════════

@router.post("/api/owner/upload/{client_id}")
async def owner_upload_asset(
    client_id: str,
    file: UploadFile = File(...),
    type: str = Form(...),
    old_path: Optional[str] = Form(None),
    auth_token: Optional[str] = Cookie(None),
):
    """Owner sirf images upload kar sakta hai (logo, banner, dish images)"""
    require_auth(auth_token, client_id=client_id, allowed_roles=["owner", "admin"])

    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if type not in OWNER_UPLOAD_RULES:
        raise HTTPException(status_code=400, detail=f"type must be: {', '.join(OWNER_UPLOAD_RULES)}")

    rule          = OWNER_UPLOAD_RULES[type]
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

    safe_name = os.path.basename(original_name).replace(" ", "_")
    folder    = os.path.join(rule["folder"], client_id)
    if not USE_R2:
        os.makedirs(folder, exist_ok=True)

    save_path = os.path.join(folder, safe_name)
    r2_key    = f"{client_id}/{safe_name}"

    # ── Purani file trash mein move karo ──
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
            if os.path.abspath(old_path) != os.path.abspath(save_path):
                move_to_trash(client_id, old_path, type)

    # ── File save ──
    if USE_R2:
        r2_upload(contents, f"{client_id}/{safe_name}", safe_name)
    else:
        with open(save_path, "wb") as f:
            f.write(contents)

    # ── Return path ──
    if USE_R2:
        path = r2_public_url(f"{client_id}/{safe_name}")
    else:
        path = f"{rule['url_prefix']}/{client_id}/{safe_name}"

    return JSONResponse({"path": path, "filename": safe_name})
