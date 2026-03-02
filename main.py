import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from database import (
    init_db, seed_tables, get_table_status,
    place_order, get_orders, update_order_status,
    generate_bill, get_bill, mark_bill_paid, get_summary,
    activate_table, close_table, get_all_tables,
    get_table_summary, get_table_orders_detail,
    get_analytics, update_ready_items
)

ALLOWED_EXTENSIONS  = {".glb", ".mind", ".png", ".jpg", ".jpeg", ".webp"}
PROTECTED_EXTENSIONS = {".glb", ".mind"}

# ════════════════════════════════
# HELPERS
# ════════════════════════════════

def get_client_data(client_id: str):
    file_path = f"data/{client_id}.json"
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        return json.load(f)

@asynccontextmanager
async def lifespan(app):
    init_db()
    # Har client ka JSON padho aur tables seed karo
    for filename in os.listdir("data"):
        if filename.endswith(".json"):
            client_id = filename.replace(".json", "")
            data = get_client_data(client_id)
            if data and "num_tables" in data.get("restaurant", {}):
                seed_tables(client_id, data["restaurant"]["num_tables"])

    templates.env.globals["static_v"] = lambda path: \
    int(os.path.getmtime(f"static/{path}")) if os.path.exists(f"static/{path}") else 0

    yield

# app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def setup_jinja():
    templates.env.globals["static_v"] = lambda path: \
        int(os.path.getmtime(f"static/{path}")) if os.path.exists(f"static/{path}") else 0

# ════════════════════════════════
# PYDANTIC MODELS
# ════════════════════════════════

class OrderItem(BaseModel):
    name: str
    qty: int
    price: int  # in rupees

class PlaceOrderRequest(BaseModel):
    items: List[OrderItem]
    total: int
    source: Optional[str] = 'customer'  # customer | waiter
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    status: str  # pending | preparing | ready | done

class BillRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    tax_percent: Optional[float] = 0.0
    discount: Optional[int] = 0
    payment_mode: Optional[str] = None

class MarkPaidRequest(BaseModel):
    payment_mode: str = 'cash'  # cash | upi | card

class ReadyItemsRequest(BaseModel):
    ready_items: List[str]

# ════════════════════════════════
# ASSET SERVING
# ════════════════════════════════

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/static/assets/{client_id}/{filename}")
async def serve_asset(request: Request, client_id: str, filename: str):
    if ".." in client_id or ".." in filename or "/" in filename:
        raise HTTPException(status_code=403, detail="Forbidden")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="File type not allowed")
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if ext in PROTECTED_EXTENSIONS:
        referer = request.headers.get("referer", "")
        host = request.headers.get("host", "")
        if not referer or host not in referer:
            raise HTTPException(status_code=403, detail="Direct access not allowed")
    file_path = f"static/assets/{client_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    response = FileResponse(file_path)
    if ext in PROTECTED_EXTENSIONS:
        response.headers["Content-Disposition"] = "inline"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
    return response

# ════════════════════════════════
# PAGE ROUTES
# ════════════════════════════════

@app.get("/{client_id}", response_class=HTMLResponse)
async def restaurant_home(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("home.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None  # 👈 ye add karo
    })

@app.get("/{client_id}/menu", response_class=HTMLResponse)
async def menu(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("menu.html", {
        "request": request, "client_id": client_id, "data": data, "table_no": None
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
        "request": request, "client_id": client_id, "data": data, "table_no": table_no
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
# MENU API
# ════════════════════════════════

@app.get("/{client_id}/staff", response_class=HTMLResponse)
async def staff_login(request: Request, client_id: str):
    """Staff login page"""
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff.html", {
        "request": request, "client_id": client_id, "data": data
    })

@app.get("/{client_id}/staff/owner", response_class=HTMLResponse)
async def staff_owner(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_owner.html", {
        "request": request, "client_id": client_id, "data": data
    })

@app.get("/{client_id}/staff/kitchen", response_class=HTMLResponse)
async def staff_kitchen(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_kitchen.html", {
        "request": request, "client_id": client_id, "data": data
    })

@app.get("/{client_id}/staff/waiter", response_class=HTMLResponse)
async def staff_waiter(request: Request, client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return templates.TemplateResponse("staff_waiter.html", {
        "request": request, "client_id": client_id, "data": data
    })

@app.get("/api/menu/{client_id}")
async def get_menu_api(client_id: str):
    data = get_client_data(client_id)
    if data:
        return JSONResponse(content=data)
    raise HTTPException(status_code=404, detail="Data not found")

# ════════════════════════════════
# TABLE API
# ════════════════════════════════

@app.post("/api/table/{client_id}/{table_no}/activate")
async def api_activate_table(client_id: str, table_no: int):
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    activate_table(client_id, table_no)
    return {"message": f"Table {table_no} activated"}

@app.post("/api/table/{client_id}/{table_no}/close")
async def api_close_table(client_id: str, table_no: int):
    close_table(client_id, table_no)
    return {"message": f"Table {table_no} closed"}

@app.get("/api/tables/{client_id}/summary")
async def api_table_summary(client_id: str):
    """Table summary with display_status — for waiter dashboard"""
    return get_table_summary(client_id)

@app.get("/api/tables/{client_id}")
async def api_get_tables(client_id: str):
    return get_all_tables(client_id)

# ════════════════════════════════
# ORDER API
# ════════════════════════════════

@app.post("/api/order/{client_id}/{table_no}")
async def api_place_order(client_id: str, table_no: int, body: PlaceOrderRequest):
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
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
# ADMIN API
# ════════════════════════════════

@app.get("/api/table/{client_id}/{table_no}/detail")
async def api_table_detail(client_id: str, table_no: int):
    """Full orders + bills for a table — for waiter tap view"""
    return get_table_orders_detail(client_id, table_no)

@app.get("/api/orders/{client_id}/filter")
async def api_filter_orders(client_id: str, status: str = None,
                             table_no: int = None, source: str = None):
    """Owner filtered orders view"""
    return get_orders(client_id, status=status, table_no=table_no, source=source)

@app.get("/api/admin/summary/{client_id}")
async def api_summary(client_id: str):
    return get_summary(client_id)

@app.get("/api/admin/analytics/{client_id}")
async def api_analytics(client_id: str):
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return get_analytics(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
