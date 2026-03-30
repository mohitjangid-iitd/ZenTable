import json
import os
import shutil
import hashlib
import hmac
import base64
import bcrypt
import copy
from datetime import datetime, timezone, timedelta
from starlette.background import BackgroundTask
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Cookie, Response, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from site_config import SITE_CONFIG
from database import (
    get_db, init_db, seed_tables, get_table_status,
    place_order, get_orders, update_order_status,
    generate_bill, get_bill, mark_bill_paid, get_summary,
    activate_table, close_table, close_all_tables, activate_all_tables, get_all_tables,
    get_table_summary, get_table_orders_detail,
    get_analytics, update_ready_items,
    create_staff, get_staff_list, update_staff_password,
    toggle_staff_active, delete_staff,
    get_all_restaurants_info, get_overall_stats, get_top_dishes_overall,
    save_restaurant_json, delete_restaurant_full,
    create_admin, export_full_db_zip
)
from auth import login_staff, login_admin, decode_token, get_redirect_url

IST = timezone(timedelta(hours=5, minutes=30))

# ════════════════════════════════
# CONFIG & CONSTANTS
# ════════════════════════════════

ALLOWED_EXTENSIONS   = {".glb", ".mind", ".png", ".jpg", ".jpeg", ".webp"}
PROTECTED_EXTENSIONS = {".glb", ".mind"}
GLB_SECRET = os.environ["GLB_SECRET"]
GLB_TOKEN_EXPIRY = 600  # 10 minutes

# ── Upload config ──
UPLOAD_RULES = {
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
        "max_mb": 10,
        "folder": "static/assets",      # static/assets/{client_id}/
        "url_prefix": "/static/assets", # public URL
    },
    "mind": {
        "extensions": {".mind"},
        "max_mb": 50,
        "folder": "static/assets",
        "url_prefix": "/static/assets",
        "fixed_name": "targets.mind",   # hamesha isi naam se save hoga
    },
    "model": {
        "extensions": {".glb", ".gltf"},
        "max_mb": 100,
        "folder": "private/assets",     # private/assets/{client_id}/
        "url_prefix": None,             # JSON mein sirf "{client_id}/file.glb" store hota hai
    },
}

# ── Trash config ──
TRASH_DIR        = "private/trash"
TRASH_META_FILE  = "private/trash/trash_meta.json"
TRASH_EXPIRY_DAYS = 30

# ════════════════════════════════
# TRASH HELPERS
# ════════════════════════════════

def _load_trash_meta() -> list:
    """trash_meta.json padho — nahi hai to empty list"""
    if not os.path.exists(TRASH_META_FILE):
        return []
    try:
        with open(TRASH_META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_trash_meta(meta: list):
    """trash_meta.json save karo"""
    os.makedirs(TRASH_DIR, exist_ok=True)
    with open(TRASH_META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

def move_to_trash(client_id: str, save_path: str, file_type: str):
    """
    Existing file ko trash mein move karo before overwrite.
    save_path  — jahan file abhi hai  (e.g. static/assets/clint_one/logo.png)
    file_type  — "image" | "model" | "mind"
    """
    if not os.path.exists(save_path):
        return  # kuch nahi hai overwrite karne ke liye

    now        = datetime.now(IST)
    ts         = int(now.timestamp())
    orig_name  = os.path.basename(save_path)
    trash_name = f"{ts}_{client_id}_{orig_name}"

    trash_client_dir = os.path.join(TRASH_DIR, client_id)
    os.makedirs(trash_client_dir, exist_ok=True)

    dest = os.path.join(trash_client_dir, trash_name)
    shutil.move(save_path, dest)

    size_kb = round(os.path.getsize(dest) / 1024, 1)
    deleted_at     = now.strftime("%Y-%m-%d %H:%M:%S")
    auto_delete_at = (now + timedelta(days=TRASH_EXPIRY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")

    meta = _load_trash_meta()
    meta.append({
        "client_id":      client_id,
        "original_name":  orig_name,
        "original_path":  save_path,       # restore ke liye
        "trash_name":     trash_name,
        "file_type":      file_type,
        "size_kb":        size_kb,
        "deleted_at":     deleted_at,
        "auto_delete_at": auto_delete_at,
    })
    _save_trash_meta(meta)

def purge_expired_trash():
    """
    30 din se purani trash files delete karo.
    Lifespan mein call hota hai — server restart pe chalta hai.
    """
    meta    = _load_trash_meta()
    now     = datetime.now(IST)
    kept    = []
    deleted = 0

    for entry in meta:
        try:
            expiry = datetime.strptime(entry["auto_delete_at"], "%Y-%m-%d %H:%M:%S")
            expiry = expiry.replace(tzinfo=IST)
        except Exception:
            kept.append(entry)
            continue

        if now > expiry:
            # File disk se delete karo
            trash_path = os.path.join(TRASH_DIR, entry["client_id"], entry["trash_name"])
            if os.path.exists(trash_path):
                os.remove(trash_path)
            deleted += 1
        else:
            kept.append(entry)

    if deleted:
        _save_trash_meta(kept)
        print(f"🗑️  Trash purge: {deleted} expired file(s) deleted")

def restore_from_trash(trash_name: str) -> bool:
    """
    Trash file ko uski original location pe wapas rakho.
    Return True on success, False if not found.
    """
    meta = _load_trash_meta()
    entry = next((e for e in meta if e["trash_name"] == trash_name), None)
    if not entry:
        return False

    trash_path    = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
    original_path = entry["original_path"]

    if not os.path.exists(trash_path):
        return False

    os.makedirs(os.path.dirname(original_path), exist_ok=True)
    shutil.move(trash_path, original_path)

    # Meta se entry hatao
    updated = [e for e in meta if e["trash_name"] != trash_name]
    _save_trash_meta(updated)
    return True

def delete_from_trash(trash_name: str) -> bool:
    """Trash se permanently delete karo."""
    meta  = _load_trash_meta()
    entry = next((e for e in meta if e["trash_name"] == trash_name), None)
    if not entry:
        return False

    trash_path = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
    if os.path.exists(trash_path):
        os.remove(trash_path)

    updated = [e for e in meta if e["trash_name"] != trash_name]
    _save_trash_meta(updated)
    return True


def create_glb_token(client_id: str, filepath: str) -> str:
    """GLB file ke liye signed token banao — 10 min expiry"""
    expires = int(datetime.now(timezone.utc).timestamp()) + GLB_TOKEN_EXPIRY
    msg = f"{client_id}:{filepath}:{expires}"
    sig = hmac.new(GLB_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    payload = base64.urlsafe_b64encode(f"{msg}:{sig}".encode()).decode()
    return payload

def verify_glb_token(token: str):
    """Token verify karo — valid hone pe (client_id, filepath) return karo"""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
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
    except:
        return None

# ════════════════════════════════
# HELPERS
# ════════════════════════════════

def get_client_data(client_id: str):
    file_path = f"data/{client_id}.json"
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        return json.load(f)

def has_feature(data: dict, feature: str) -> bool:
    """Restaurant ke liye feature enabled hai ya nahi"""
    features = data.get("subscription", {}).get("features", ["basic"])
    return feature in features

def require_feature(data: dict, feature: str):
    """Feature nahi hai to 403"""
    if not has_feature(data, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' not available")

def is_restaurant_active(data: dict) -> bool:
    return data.get("subscription", {}).get("active", True)

def closed_response(request, data, client_id):
    return RedirectResponse(url=SITE_CONFIG["instagram"], status_code=302)

def get_current_user(token: Optional[str]) -> Optional[dict]:
    """Cookie se token padho aur decode karo"""
    if not token:
        return None
    return decode_token(token)

def require_auth(token: Optional[str], allowed_roles: list, client_id: str = None) -> dict:
    user = get_current_user(token)
    if not user:
        login_url = "/admin/login" if allowed_roles == ["admin"] else "/login"
        raise HTTPException(
            status_code=302,
            headers={
                "Location": login_url,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache"
            }
        )
    if user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied")
    if client_id and user.get("role") != "admin":
        if user.get("restaurant_id") != client_id:
            raise HTTPException(status_code=403, detail="Access denied — wrong restaurant")
    return user

# ════════════════════════════════
# LIFESPAN
# ════════════════════════════════

@asynccontextmanager
async def lifespan(app):
    init_db()
    purge_expired_trash()   # Server start pe expired trash files clean karo
    for filename in os.listdir("data"):
        if filename.endswith(".json"):
            client_id = filename.replace(".json", "")
            data = get_client_data(client_id)
            if data and "num_tables" in data.get("restaurant", {}):
                seed_tables(client_id, data["restaurant"]["num_tables"])

    templates.env.globals["static_v"] = lambda path: \
        int(os.path.getmtime(f"static/{path}")) if os.path.exists(f"static/{path}") else 0
    
    templates.env.globals["site"] = SITE_CONFIG
    
    yield

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# ════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════

class OrderItem(BaseModel):
    name: str
    qty: int
    price: int

class PlaceOrderRequest(BaseModel):
    items: List[OrderItem]
    total: int
    source: Optional[str] = 'customer'
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    status: str

class BillRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    tax_percent: Optional[float] = 0.0
    discount: Optional[int] = 0
    payment_mode: Optional[str] = None

class MarkPaidRequest(BaseModel):
    payment_mode: str = 'cash'

class ReadyItemsRequest(BaseModel):
    ready_items: list  # List[str] ya List[{name,qty}] dono accept

class EditOrderItemsRequest(BaseModel):
    items: List[dict]           # [{name, qty, price}]
    extra_items: List[dict] = []  # [{name, qty, price}] — waiter ne baad mein add kiye

class LoginRequest(BaseModel):
    username: str
    password: str
    restaurant_id: Optional[str] = None  # staff ke liye, admin ke liye None

class CreateStaffRequest(BaseModel):
    username: str
    password: str
    name: str
    role: str  # owner | kitchen | waiter | counter

class UpdatePasswordRequest(BaseModel):
    new_password: str

class CreateAdminRequest(BaseModel):
    name: str
    username: str
    password: str

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

# ════════════════════════════════
# Uptimerobot ping route
# ════════════════════════════════

@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return {"status": "ok"}

# ════════════════════════════════
# Landing Page
# ════════════════════════════════

@app.get("/")
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "config": SITE_CONFIG
    })

# ════════════════════════════════
# ASSET SERVING
# ════════════════════════════════

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/static/assets/{client_id}/{filename}")
async def serve_asset(request: Request, client_id: str, filename: str):
    if ".." in client_id or ".." in filename or "/" in filename:
        raise HTTPException(status_code=403, detail="Forbidden")
    ext = os.path.splitext(filename)[1].lower()
    # GLB/mind ab is route se serve nahi honge — /glb/{token} se serve honge
    if ext in PROTECTED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Use signed URL")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="File type not allowed")
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    file_path = f"static/assets/{client_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path)

# ════════════════════════════════
# LOGIN / LOGOUT
# ════════════════════════════════

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = get_current_user(auth_token)
    if user and user.get("role") == "admin":
        return RedirectResponse(url="/admin")
    return templates.TemplateResponse("admin_login.html", {"request": request, "site": SITE_CONFIG})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, auth_token: Optional[str] = Cookie(None)):
    """Login page — sirf staff logged in ho toh redirect karo, admin ko nahi"""
    user = get_current_user(auth_token)
    if user and user.get("role") != "admin":
        redirect_url = get_redirect_url(user["role"], user.get("restaurant_id"))
        return RedirectResponse(url=redirect_url)
    return templates.TemplateResponse("login.html", {"request": request, "site": SITE_CONFIG})

@app.post("/api/auth/login")
async def api_login(body: LoginRequest, response: Response):
    """
    Staff: restaurant_id + username + password
    Admin: username + password (restaurant_id = None)
    """
    if body.restaurant_id:
        # Staff login — pehle restaurant active hai ya nahi check karo
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
        # Admin login
        token, user = login_admin(body.username, body.password)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        redirect_url = get_redirect_url("admin")

    # Cookie mein token set karo
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,       # JS se access nahi hoga
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 days max (role expiry auth.py mein handle hoti hai)
    )
    return {"redirect": redirect_url, "role": user["role"], "name": user["name"]}

@app.post("/api/auth/logout")
async def api_logout(response: Response):
    response.delete_cookie("auth_token")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {"redirect": "/login"}

@app.get("/logout")
async def logout_redirect(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.delete_cookie("auth_token")
    return RedirectResponse(url="/login")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["admin"])
    response = templates.TemplateResponse("admin.html", {
        "request": request, "site": SITE_CONFIG, "user": user
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

# ════════════════════════════════
# ADMIN APIs
# ════════════════════════════════

@app.get("/api/admin/overview")
async def api_admin_overview(period: str = "alltime", auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    restaurants = get_all_restaurants_info()
    for r in restaurants:
        rdata = get_client_data(r["client_id"]) or {}
        r["active"] = rdata.get("subscription", {}).get("active", True)
    return {
        "stats": get_overall_stats(),
        "restaurants": restaurants,
        "top_dishes": get_top_dishes_overall(10, period),
    }

@app.get("/api/admin/restaurant/{client_id}/analytics")
async def api_admin_restaurant_analytics(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return get_analytics(client_id)

@app.get("/api/admin/restaurant/{client_id}/json")
async def api_get_restaurant_json(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return data

@app.put("/api/admin/restaurant/{client_id}/json")
async def api_save_restaurant_json(client_id: str, body: SaveRestaurantRequest,
                                    auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    save_restaurant_json(client_id, body.data)
    return {"message": "Saved"}

@app.post("/api/admin/restaurant")
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
            "logo": f"/static/assets/{client_id}/logo.png",
            "banner": f"/static/assets/{client_id}/banner.png",
            "description": body.description, "cuisine_type": body.cuisine_type,
            "phone": body.phone, "email": body.email, "address": body.address,
            "timings": {"lunch": body.lunch, "dinner": body.dinner, "closed": body.closed},
            "social": {"instagram": body.instagram, "facebook": body.facebook, "twitter": body.twitter}
        },
        "theme": {
            "primary_color": "#D4AF37", "secondary_color": "#1a1a1a",
            "accent_color": "#8B4513", "text_color": "#333333",
            "background": "#ffffff", "font_primary": "Playfair Display",
            "font_secondary": "Poppins"
        },
        "subscription": {
            "features": ["basic"]
        },
        "items": []
    }
    os.makedirs("data", exist_ok=True)
    os.makedirs(f"static/assets/{client_id}", exist_ok=True)
    os.makedirs(f"private/assets/{client_id}", exist_ok=True)
    save_restaurant_json(client_id, data)
    seed_tables(client_id, body.num_tables)
    return {"message": f"Restaurant {client_id} created", "client_id": client_id}

# ════════════════════════════════
# UPLOAD API
# ════════════════════════════════

@app.post("/api/admin/upload/{client_id}")
async def api_upload_asset(
    client_id: str,
    file: UploadFile = File(...),
    type: str = Form(...),           # "image" | "model" | "mind"
    old_path: Optional[str] = Form(None),  # purani file ka path — frontend se bhejo, trash ho jayegi
    auth_token: Optional[str] = Cookie(None),
):
    require_auth(auth_token, ["admin"])

    # ── Restaurant exist karta hai? ──
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # ── file type valid hai? ──
    if type not in UPLOAD_RULES:
        raise HTTPException(status_code=400, detail=f"type must be: {', '.join(UPLOAD_RULES)}")

    rule = UPLOAD_RULES[type]

    # ── Extension check ──
    original_name = file.filename or "upload"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in rule["extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"'{ext}' allowed nahi. Allowed: {', '.join(rule['extensions'])}"
        )

    # ── File size check ──
    contents = await file.read()
    max_bytes = rule["max_mb"] * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File bahut badi hai. Max {rule['max_mb']}MB allowed."
        )

    # ── Filename sanitize (path traversal se bachao) ──
    safe_name = rule.get("fixed_name") or os.path.basename(original_name).replace(" ", "_")

    # ── Folder banao ──
    folder = os.path.join(rule["folder"], client_id)
    os.makedirs(folder, exist_ok=True)

    # ── Purani file trash mein move karo (agar exist karti hai) ──
    # mind files (targets.mind) trash mein nahi jayengi — seedha overwrite
    save_path = os.path.join(folder, safe_name)
    if type != "mind":
        # 1. Same naam ki file ho to trash karo (direct overwrite case)
        move_to_trash(client_id, save_path, type)

        # 2. Frontend ne old_path bheja ho (alag naam wali purani file) to usse bhi trash karo
        #    Model case: "clint_two/pizza.glb" → private/assets/clint_two/pizza.glb
        #    Image case: "/static/assets/clint_two/old_logo.png" → static/assets/clint_two/old_logo.png
        if old_path and old_path.strip().lower() not in ("", "none"):
            old_path = old_path.strip().lstrip("/")  # leading slash hata do
            old_full = os.path.join("private/assets", old_path) if type == "model" \
                       else old_path  # image path already has static/assets/... prefix
            # Sirf tabhi trash karo agar yeh save_path se alag file hai
            if os.path.abspath(old_full) != os.path.abspath(save_path):
                move_to_trash(client_id, old_full, type)

    # ── File save karo (overwrite) ──
    save_path = os.path.join(folder, safe_name)
    with open(save_path, "wb") as f:
        f.write(contents)

    # ── URL/path return karo (JSON mein store hone wala value) ──
    if rule["url_prefix"]:
        path = f"{rule['url_prefix']}/{client_id}/{safe_name}"
    else:
        # model: sirf "client_id/filename" — /glb/{token} route isse use karta hai
        path = f"{client_id}/{safe_name}"

    return JSONResponse({"path": path, "filename": safe_name})

@app.get("/api/admin/restaurant/{client_id}/assets-zip")
async def api_download_assets_zip(
    client_id: str,
    folder: str,  # "static" ya "private"
    auth_token: Optional[str] = Cookie(None)
):
    """Assets ka zip banao aur download karo"""
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")

    import shutil, tempfile, zipfile

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

    # Temp zip file banao
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname  = os.path.relpath(filepath, assets_dir)
                zf.write(filepath, arcname)
    tmp.close()

    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename=zip_name,
        background=None
    )

@app.delete("/api/admin/restaurant/{client_id}")
async def api_delete_restaurant(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    delete_restaurant_full(client_id)

    # Asset folders bhi delete karo (static + private)
    import shutil
    for assets_dir in [f"static/assets/{client_id}", f"private/assets/{client_id}"]:
        if os.path.exists(assets_dir):
            shutil.rmtree(assets_dir, ignore_errors=True)

    return {"message": f"Restaurant {client_id} deleted"}

@app.patch("/api/admin/restaurant/{client_id}/toggle")
async def api_toggle_restaurant(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    current = data.get("subscription", {}).get("active", True)
    new_state = not current
    if "subscription" not in data:
        data["subscription"] = {"features": ["basic"]}
    data["subscription"]["active"] = new_state
    save_restaurant_json(client_id, data)
    return {"active": new_state}

@app.get("/api/admin/staff/{client_id}")
async def api_admin_get_staff(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    return get_staff_list(client_id)

@app.post("/api/admin/staff/{client_id}")
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

@app.patch("/api/admin/staff/{staff_id}/password")
async def api_admin_update_password(staff_id: int, body: UpdatePasswordRequest,
                                     auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    update_staff_password(staff_id, body.new_password)
    return {"message": "Password updated"}

@app.patch("/api/admin/staff/{staff_id}/toggle")
async def api_admin_toggle_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    conn = get_db()
    row = conn.execute("SELECT is_active FROM staff WHERE id=%s", (staff_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    new_state = not bool(row[0])
    toggle_staff_active(staff_id, new_state)
    return {"message": "Updated", "is_active": new_state}

@app.delete("/api/admin/staff/{staff_id}")
async def api_admin_delete_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    delete_staff(staff_id)
    return {"message": "Staff deleted"}

@app.post("/api/admin/create")
async def api_create_admin(body: CreateAdminRequest, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not body.name or not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Sab fields required hain")
    ok = create_admin(body.username, body.password, body.name)
    if not ok:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": f"Admin '{body.name}' created"}

@app.patch("/api/admin/password")
async def api_admin_change_own_password(body: UpdatePasswordRequest,
                                         auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["admin"])
    if not body.new_password:
        raise HTTPException(status_code=400, detail="Password required") 
    password_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    conn.execute("UPDATE admins SET password_hash=%s WHERE id=%s",
        (password_hash, user["admin_id"]))
    conn.commit()
    conn.close()
    return {"message": "Password updated"}

@app.get("/api/admin/export/db-zip")
async def api_export_db_zip(auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    zip_path = export_full_db_zip()
    filename = f"zentable_db_{datetime.now(IST).strftime('%d-%m-%Y_%H-%M')}_IST.zip"
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
        background=BackgroundTask(os.remove, zip_path)
    )

# ════════════════════════════════
# TRASH API
# ════════════════════════════════

@app.get("/api/admin/trash")
async def api_get_trash(client_id: str = None, auth_token: Optional[str] = Cookie(None)):
    """
    Saari trash files list karo.
    client_id query param dene pe usi restaurant ki files filter hongi.
    Har entry mein 'days_left' bhi hoga.
    """
    require_auth(auth_token, ["admin"])
    meta = _load_trash_meta()
    now  = datetime.now(IST)

    result = []
    for entry in meta:
        if client_id and entry["client_id"] != client_id:
            continue
        try:
            expiry   = datetime.strptime(entry["auto_delete_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
            days_left = max(0, (expiry - now).days)
        except Exception:
            days_left = None
        result.append({**entry, "days_left": days_left})

    # Naye pehle
    result.sort(key=lambda x: x["deleted_at"], reverse=True)
    return result

@app.post("/api/admin/trash/{trash_name}/restore")
async def api_restore_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    """Trash file ko uski original location pe wapas rakho."""
    require_auth(auth_token, ["admin"])
    ok = restore_from_trash(trash_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila ya file missing hai")
    return {"message": f"'{trash_name}' restore ho gayi"}

@app.delete("/api/admin/trash/{trash_name}")
async def api_delete_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    """Trash file permanently delete karo."""
    require_auth(auth_token, ["admin"])
    ok = delete_from_trash(trash_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila")
    return {"message": f"'{trash_name}' permanently delete ho gayi"}

@app.get("/api/admin/trash/{trash_name}/download")
async def api_download_trash(trash_name: str, auth_token: Optional[str] = Cookie(None)):
    """Trash file download karo — direct file serve"""
    require_auth(auth_token, ["admin"])
    meta  = _load_trash_meta()
    entry = next((e for e in meta if e["trash_name"] == trash_name), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Trash entry nahi mila")
    trash_path = os.path.join(TRASH_DIR, entry["client_id"], trash_name)
    if not os.path.exists(trash_path):
        raise HTTPException(status_code=404, detail="File disk pe nahi mili")
    return FileResponse(
        trash_path,
        filename=entry["original_name"],
        media_type="application/octet-stream"
    )

@app.delete("/api/admin/trash")
async def api_empty_trash(client_id: str = None, auth_token: Optional[str] = Cookie(None)):
    """
    Saari trash empty karo.
    client_id dene pe sirf usi restaurant ki trash saaf hogi.
    """
    require_auth(auth_token, ["admin"])
    meta    = _load_trash_meta()
    removed = 0

    for entry in meta:
        if client_id and entry["client_id"] != client_id:
            continue
        trash_path = os.path.join(TRASH_DIR, entry["client_id"], entry["trash_name"])
        if os.path.exists(trash_path):
            os.remove(trash_path)
        removed += 1

    if client_id:
        updated = [e for e in meta if e["client_id"] != client_id]
    else:
        updated = []

    _save_trash_meta(updated)
    return {"message": f"{removed} file(s) permanently delete ki gayi"}

# ════════════════════════════════
# PUBLIC PAGE ROUTES
# ════════════════════════════════

@app.get("/{client_id}", response_class=HTMLResponse)
async def restaurant_home(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/menu", response_class=HTMLResponse)
async def menu(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/table/{table_no}/menu", response_class=HTMLResponse)
async def table_menu(request: Request, client_id: str, table_no: int):
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
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/ar-menu", response_class=HTMLResponse)
async def ar_menu(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    features = data.get("subscription", {}).get("features", [])
    if "ar_menu" not in features:
        return RedirectResponse(url=f"/{client_id}/menu")
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, "client_id": client_id, "table_no": None
    })

@app.get("/{client_id}/table/{table_no}", response_class=HTMLResponse)
async def table_home(request: Request, client_id: str, table_no: int):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if not is_restaurant_active(data):
        return closed_response(request, data, client_id)
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active. Please ask staff.")
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": table_no
    })

@app.get("/{client_id}/table/{table_no}/ar-menu", response_class=HTMLResponse)
async def table_ar_menu(request: Request, client_id: str, table_no: int):
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
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, "client_id": client_id, "table_no": table_no
    })

# ════════════════════════════════
# PROTECTED STAFF PAGE ROUTES
# ════════════════════════════════

@app.get("/{client_id}/staff/owner", response_class=HTMLResponse)
async def staff_owner(request: Request, client_id: str,
                      auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_owner.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/{client_id}/staff/kitchen", response_class=HTMLResponse)
async def staff_kitchen(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["kitchen", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_kitchen.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/{client_id}/staff/waiter", response_class=HTMLResponse)
async def staff_waiter(request: Request, client_id: str,
                       auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_waiter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/{client_id}/staff/counter", response_class=HTMLResponse)
async def staff_counter(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    response = templates.TemplateResponse("staff_counter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

# ════════════════════════════════
# STAFF MANAGEMENT API (owner only)
# ════════════════════════════════

@app.get("/api/staff/{client_id}")
async def api_get_staff(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["owner", "admin"], client_id)
    return get_staff_list(client_id)

@app.post("/api/staff/{client_id}")
async def api_create_staff(client_id: str, body: CreateStaffRequest,
                           auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["owner", "admin"], client_id)
    valid_roles = {"owner", "kitchen", "waiter", "counter"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Use: {valid_roles}")
    success = create_staff(client_id, body.username, body.password, body.name, body.role)
    if not success:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"message": f"Staff '{body.username}' created"}

@app.patch("/api/staff/{staff_id}/password")
async def api_update_password(staff_id: int, body: UpdatePasswordRequest,
                              auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["owner", "admin"])
    update_staff_password(staff_id, body.new_password)
    return {"message": "Password updated"}

@app.patch("/api/staff/{staff_id}/toggle")
async def api_toggle_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["owner", "admin"])
    # Active/inactive toggle — frontend se current state bhejo
    conn = get_db()
    row = conn.execute("SELECT is_active FROM staff WHERE id=%s", (staff_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Staff not found")
    new_state = not bool(row[0])
    toggle_staff_active(staff_id, new_state)
    return {"message": "Updated", "is_active": new_state}

@app.delete("/api/staff/{staff_id}")
async def api_delete_staff(staff_id: int, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["owner", "admin"])
    delete_staff(staff_id)
    return {"message": "Staff deleted"}

# ════════════════════════════════
# MENU API
# ════════════════════════════════

@app.get("/api/menu/{client_id}")
async def get_menu_api(client_id: str, request: Request):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    # GLB items ke liye signed URLs inject karo
    safe_data = copy.deepcopy(data)
    for item in safe_data.get("items", []):
        model = item.get("model")
        if model and model.lower() != "none":
            token = create_glb_token(client_id, model)
            item["model_url"] = f"/glb/{token}"
        else:
            item["model_url"] = None
    return JSONResponse(content=safe_data)

@app.get("/glb/{token}")
async def serve_glb(token: str):
    """Signed token se GLB file serve karo"""
    result = verify_glb_token(token)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    client_id, filepath = result
    # private/ folder se serve karo
    file_path = f"private/assets/{filepath}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model not found")
    return FileResponse(
        file_path,
        media_type="model/gltf-binary",
        headers={
            "Cache-Control": "no-store, no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline"
        }
    )

# ════════════════════════════════
# TABLE API
# ════════════════════════════════

@app.post("/api/table/{client_id}/{table_no}/activate")
async def api_activate_table(client_id: str, table_no: int,
                             auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    activate_table(client_id, table_no)
    return {"message": f"Table {table_no} activated"}

@app.post("/api/table/{client_id}/activate-all")
async def api_activate_all_tables(client_id: str,
                                  auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    activate_all_tables(client_id)
    return {"message": "All tables activated"}

@app.post("/api/table/{client_id}/{table_no}/close")
async def api_close_table(client_id: str, table_no: int,
                          auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    close_table(client_id, table_no)
    return {"message": f"Table {table_no} closed"}

@app.post("/api/table/{client_id}/close-all")
async def api_close_all_tables(client_id: str,
                               auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    close_all_tables(client_id)
    return {"message": "All tables closed"}

@app.get("/api/tables/{client_id}/summary")
async def api_table_summary(client_id: str):
    return get_table_summary(client_id)

@app.get("/api/tables/{client_id}")
async def api_get_tables(client_id: str):
    return get_all_tables(client_id)

# ════════════════════════════════
# ORDER API
# ════════════════════════════════

@app.post("/api/order/{client_id}/{table_no}")
async def api_place_order(client_id: str, table_no: int, body: PlaceOrderRequest):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    require_feature(data, "ordering")
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active")
    items = [i.dict() for i in body.items]
    order_id = place_order(
        client_id, table_no, items, body.total,
        body.source or 'customer',
        body.customer_name, body.customer_phone
    )
    return {"order_id": order_id, "message": "Order placed successfully"}

@app.get("/api/orders/{client_id}")
async def api_get_orders(client_id: str, status: str = None, table_no: int = None,
                         auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    return get_orders(client_id, status=status, table_no=table_no)

@app.patch("/api/order/{order_id}/status")
async def api_update_order_status(order_id: int, body: UpdateStatusRequest,
                                   auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["kitchen", "waiter", "counter", "owner", "admin"])
    valid = {"pending", "preparing", "ready", "done", "cancelled"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid}")
    update_order_status(order_id, body.status)
    return {"message": f"Order {order_id} → {body.status}"}

@app.patch("/api/order/{order_id}/ready-items")
async def api_update_ready_items(order_id: int, body: ReadyItemsRequest):
    update_ready_items(order_id, body.ready_items)
    return {"message": f"Order {order_id} ready items updated"}

@app.patch("/api/order/{order_id}/items")
async def api_edit_order_items(order_id: int, body: EditOrderItemsRequest,
                                request: Request):
    auth_token = request.cookies.get("auth_token")
    require_auth(auth_token, ["waiter", "owner", "admin"])
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=%s", (order_id,)).fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    order = dict(order)
    if order["status"] in ("done", "cancelled", "paid"):
        conn.close()
        raise HTTPException(status_code=400, detail="Order already done/cancelled")

    old_items   = json.loads(order["items"])
    ready_raw   = json.loads(order.get("ready_items") or "[]")
    old_qty_map = {i["name"]: i["qty"] for i in old_items}

    # ready_qty_map — {name: ready_qty}
    # List[str] legacy: ready_qty = old qty (jo kitchen ne ready kiya tha)
    # List[{name,qty}] new format
    ready_qty_map = {}
    for r in ready_raw:
        if isinstance(r, dict):
            ready_qty_map[r["name"]] = r["qty"]
        else:
            ready_qty_map[str(r)] = old_qty_map.get(str(r), 0)

    new_items      = []
    new_ready_list = []  # updated ready_items — qty-aware

    for item in body.items:
        name  = item["name"]
        qty   = item["qty"]
        price = item["price"]
        ready_qty = ready_qty_map.get(name, 0)

        # qty ready_qty se kam nahi ho sakti
        if qty < ready_qty:
            qty = ready_qty

        if qty <= 0:
            continue

        new_items.append({"name": name, "qty": qty, "price": price})

        # ready_items update — agar qty badhi toh ready_qty same rehti hai
        # (naya added qty pending rahega kitchen mein)
        if ready_qty > 0:
            new_ready_list.append({"name": name, "qty": ready_qty})

    if not new_items:
        conn.execute("UPDATE orders SET status='cancelled' WHERE id=%s", (order_id,))
        conn.commit()
        conn.close()
        return {"message": "Order cancelled — no items left"}

    new_total = sum(i["qty"] * i["price"] for i in new_items)
    conn.execute(
        "UPDATE orders SET items=%s, total=%s, ready_items=%s WHERE id=%s",
        (json.dumps(new_items), new_total, json.dumps(new_ready_list), order_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Order updated", "items": new_items, "total": new_total}

# ════════════════════════════════
# BILL API
# ════════════════════════════════

@app.post("/api/bill/{bill_id}/pay")
async def api_mark_paid(bill_id: int, body: MarkPaidRequest):
    mark_bill_paid(bill_id, body.payment_mode)
    return {"message": f"Bill {bill_id} marked as paid via {body.payment_mode}"}

@app.post("/api/bill/{client_id}/{table_no}")
async def api_generate_bill(client_id: str, table_no: int, body: BillRequest):
    bill = generate_bill(
        client_id, table_no,
        body.customer_name, body.customer_phone,
        body.tax_percent, body.discount, body.payment_mode
    )
    if not bill:
        raise HTTPException(
            status_code=404,
            detail="No billable orders found. Orders must be marked 'done' by kitchen before billing, and must not already be paid."
        )
    return bill

@app.get("/api/bill/{bill_id}")
async def api_get_bill(bill_id: int):
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill

# ════════════════════════════════
# ADMIN / ANALYTICS API
# ════════════════════════════════

@app.get("/api/table/{client_id}/{table_no}/detail")
async def api_table_detail(client_id: str, table_no: int):
    return get_table_orders_detail(client_id, table_no)

@app.get("/api/orders/{client_id}/filter")
async def api_filter_orders(client_id: str, status: str = None,
                             table_no: int = None, source: str = None,
                             from_date: str = None):
    if status == "kitchen":
        p = get_orders(client_id, status="pending",   table_no=table_no, source=source, from_date=from_date)
        r = get_orders(client_id, status="preparing", table_no=table_no, source=source, from_date=from_date)
        return sorted(p + r, key=lambda x: x["created_at"], reverse=True)
    return get_orders(client_id, status=status, table_no=table_no, source=source, from_date=from_date)

@app.get("/api/admin/summary/{client_id}")
async def api_summary(client_id: str):
    return get_summary(client_id)

@app.get("/api/admin/analytics/{client_id}")
async def api_analytics(client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    require_feature(data, "analytics")
    return get_analytics(client_id)

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
