import json
import os
import hashlib
import hmac
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from site_config import SITE_CONFIG
from database import (
    init_db, seed_tables, get_table_status,
    place_order, get_orders, update_order_status,
    generate_bill, get_bill, mark_bill_paid, get_summary,
    activate_table, close_table, close_all_tables, activate_all_tables, get_all_tables,
    get_table_summary, get_table_orders_detail,
    get_analytics, update_ready_items,
    create_staff, get_staff_list, update_staff_password,
    toggle_staff_active, delete_staff,
    get_all_restaurants_info, get_overall_stats, get_top_dishes_overall,
    save_restaurant_json, delete_restaurant_full,
    create_admin
)
from auth import login_staff, login_admin, decode_token, get_redirect_url

ALLOWED_EXTENSIONS   = {".glb", ".mind", ".png", ".jpg", ".jpeg", ".webp"}
PROTECTED_EXTENSIONS = {".glb", ".mind"}
GLB_SECRET = os.environ.get("GLB_SECRET", "glb-secret-change-in-production")
GLB_TOKEN_EXPIRY = 600  # 10 minutes

def create_glb_token(client_id: str, filepath: str) -> str:
    """GLB file ke liye signed token banao — 10 min expiry"""
    expires = int(time.time()) + GLB_TOKEN_EXPIRY
    msg = f"{client_id}:{filepath}:{expires}"
    sig = hmac.new(GLB_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:16]
    import base64
    payload = base64.urlsafe_b64encode(f"{msg}:{sig}".encode()).decode()
    return payload

def verify_glb_token(token: str):
    """Token verify karo — valid hone pe (client_id, filepath) return karo"""
    try:
        import base64
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
        if int(time.time()) > int(expires_str):
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

def get_current_user(token: Optional[str]) -> Optional[dict]:
    """Cookie se token padho aur decode karo"""
    if not token:
        return None
    return decode_token(token)

def require_auth(token: Optional[str], allowed_roles: list, client_id: str = None) -> dict:
    """
    Auth check — unauthorized hone pe redirect raise karta hai.
    client_id diya ho toh restaurant match bhi check karta hai.
    """
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
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

app = FastAPI(lifespan=lifespan)
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
    ready_items: List[str]

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
        # Staff login
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
    return {"redirect": "/login"}

@app.get("/logout")
async def logout_redirect(response: Response):
    response.delete_cookie("auth_token")
    return RedirectResponse(url="/login")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["admin"])
    return templates.TemplateResponse("admin.html", {"request": request, "site": SITE_CONFIG, "user": user})

# ════════════════════════════════
# ADMIN APIs
# ════════════════════════════════

@app.get("/api/admin/overview")
async def api_admin_overview(auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    return {
        "stats": get_overall_stats(),
        "restaurants": get_all_restaurants_info(),
        "top_dishes": get_top_dishes_overall(10),
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
    save_restaurant_json(client_id, data)
    seed_tables(client_id, body.num_tables)
    return {"message": f"Restaurant {client_id} created", "client_id": client_id}

@app.delete("/api/admin/restaurant/{client_id}")
async def api_delete_restaurant(client_id: str, auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["admin"])
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    delete_restaurant_full(client_id)
    return {"message": f"Restaurant {client_id} deleted"}

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
    from database import get_db
    conn = get_db()
    row = conn.execute("SELECT is_active FROM staff WHERE id=?", (staff_id,)).fetchone()
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
    from database import get_db
    import bcrypt
    password_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    conn.execute("UPDATE admins SET password_hash=? WHERE id=?",
                 (password_hash, user["admin_id"]))
    conn.commit()
    conn.close()
    return {"message": "Password updated"}

# ════════════════════════════════
# PUBLIC PAGE ROUTES
# ════════════════════════════════

@app.get("/{client_id}", response_class=HTMLResponse)
async def restaurant_home(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/menu", response_class=HTMLResponse)
async def menu(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/table/{table_no}/menu", response_class=HTMLResponse)
async def table_menu(request: Request, client_id: str, table_no: int):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active. Please ask staff.")
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": table_no,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/ar-menu", response_class=HTMLResponse)
async def ar_menu(request: Request, client_id: str):
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("ar_menu.html", {
        "request": request, "client_id": client_id, "table_no": None
    })

@app.get("/{client_id}/table/{table_no}", response_class=HTMLResponse)
async def table_home(request: Request, client_id: str, table_no: int):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
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
    return templates.TemplateResponse("staff_owner.html", {
        "request": request, "client_id": client_id, "data": data, "user": user,
        "features": data.get("subscription", {}).get("features", ["basic"])
    })

@app.get("/{client_id}/staff/kitchen", response_class=HTMLResponse)
async def staff_kitchen(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["kitchen", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_kitchen.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })

@app.get("/{client_id}/staff/waiter", response_class=HTMLResponse)
async def staff_waiter(request: Request, client_id: str,
                       auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_waiter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })

@app.get("/{client_id}/staff/counter", response_class=HTMLResponse)
async def staff_counter(request: Request, client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_counter.html", {
        "request": request, "client_id": client_id, "data": data, "user": user
    })

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
    from database import get_db
    conn = get_db()
    row = conn.execute("SELECT is_active FROM staff WHERE id=?", (staff_id,)).fetchone()
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
    import copy
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
async def api_get_orders(client_id: str, status: str = None, table_no: int = None):
    return get_orders(client_id, status=status, table_no=table_no)

@app.patch("/api/order/{order_id}/status")
async def api_update_order_status(order_id: int, body: UpdateStatusRequest):
    valid = {"pending", "preparing", "ready", "done", "cancelled"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid}")
    update_order_status(order_id, body.status)
    return {"message": f"Order {order_id} → {body.status}"}

@app.patch("/api/order/{order_id}/ready-items")
async def api_update_ready_items(order_id: int, body: ReadyItemsRequest):
    update_ready_items(order_id, body.ready_items)
    return {"message": f"Order {order_id} ready items updated"}

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
                             table_no: int = None, source: str = None):
    return get_orders(client_id, status=status, table_no=table_no, source=source)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
