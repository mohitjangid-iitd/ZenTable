"""
routers/orders.py — Orders + Bills API

POST  /api/order/{client_id}/{table_no}
GET   /api/orders/{client_id}
GET   /api/orders/{client_id}/filter
PATCH /api/order/{order_id}/status
PATCH /api/order/{order_id}/ready-items
PATCH /api/order/{order_id}/items
POST  /api/bill/{client_id}/{table_no}
POST  /api/bill/{bill_id}/pay
GET   /api/bill/{bill_id}
"""

import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Cookie, Request
from pydantic import BaseModel

from database import (
    get_db,
    place_order, get_orders, update_order_status,
    update_ready_items, generate_bill, get_bill, mark_bill_paid,
    get_table_status,
)
from helpers import get_client_data, require_feature, require_auth

router = APIRouter()


# ── Pydantic models ──

class OrderItem(BaseModel):
    name: str
    qty: int
    price: int

class PlaceOrderRequest(BaseModel):
    items: List[OrderItem]
    total: int
    source: Optional[str] = "customer"
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    status: str

class ReadyItemsRequest(BaseModel):
    ready_items: list

class EditOrderItemsRequest(BaseModel):
    items: List[dict]
    extra_items: List[dict] = []

class BillRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    tax_percent: Optional[float] = 0.0
    discount: Optional[int] = 0
    payment_mode: Optional[str] = None

class MarkPaidRequest(BaseModel):
    payment_mode: str = "cash"


# ── Routes ──

@router.post("/api/order/{client_id}/{table_no}")
async def api_place_order(client_id: str, table_no: int, body: PlaceOrderRequest):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    require_feature(data, "ordering")
    table = get_table_status(client_id, table_no)
    if not table or table["status"] == "inactive":
        raise HTTPException(status_code=403, detail="Table not active")
    items    = [i.dict() for i in body.items]
    order_id = place_order(
        client_id, table_no, items, body.total,
        body.source or "customer",
        body.customer_name, body.customer_phone,
    )
    return {"order_id": order_id, "message": "Order placed successfully"}


@router.get("/api/orders/{client_id}")
async def api_get_orders(client_id: str, status: str = None, table_no: int = None,
                         auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["kitchen", "waiter", "counter", "owner", "admin"], client_id)
    return get_orders(client_id, status=status, table_no=table_no)


@router.get("/api/orders/{client_id}/filter")
async def api_filter_orders(client_id: str, status: str = None,
                             table_no: int = None, source: str = None,
                             from_date: str = None):
    if status == "kitchen":
        p = get_orders(client_id, status="pending",   table_no=table_no, source=source, from_date=from_date)
        r = get_orders(client_id, status="preparing", table_no=table_no, source=source, from_date=from_date)
        return sorted(p + r, key=lambda x: x["created_at"], reverse=True)
    return get_orders(client_id, status=status, table_no=table_no, source=source, from_date=from_date)


@router.patch("/api/order/{order_id}/status")
async def api_update_order_status(order_id: int, body: UpdateStatusRequest,
                                   auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["kitchen", "waiter", "counter", "owner", "admin"])
    valid = {"pending", "preparing", "ready", "done", "cancelled"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid}")
    update_order_status(order_id, body.status)
    return {"message": f"Order {order_id} → {body.status}"}


@router.patch("/api/order/{order_id}/ready-items")
async def api_update_ready_items(order_id: int, body: ReadyItemsRequest):
    update_ready_items(order_id, body.ready_items)
    return {"message": f"Order {order_id} ready items updated"}


@router.patch("/api/order/{order_id}/items")
async def api_edit_order_items(order_id: int, body: EditOrderItemsRequest,
                                request: Request):
    auth_token = request.cookies.get("auth_token")
    require_auth(auth_token, ["waiter", "owner", "admin"])

    conn  = get_db()
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

    ready_qty_map = {}
    for r in ready_raw:
        if isinstance(r, dict):
            ready_qty_map[r["name"]] = r["qty"]
        else:
            ready_qty_map[str(r)] = old_qty_map.get(str(r), 0)

    new_items      = []
    new_ready_list = []

    for item in body.items:
        name      = item["name"]
        qty       = item["qty"]
        price     = item["price"]
        ready_qty = ready_qty_map.get(name, 0)

        if qty < ready_qty:
            qty = ready_qty
        if qty <= 0:
            continue

        new_items.append({"name": name, "qty": qty, "price": price})
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


@router.post("/api/bill/{bill_id}/pay")
async def api_mark_paid(bill_id: int, body: MarkPaidRequest):
    mark_bill_paid(bill_id, body.payment_mode)
    return {"message": f"Bill {bill_id} marked as paid via {body.payment_mode}"}


@router.post("/api/bill/{client_id}/{table_no}")
async def api_generate_bill(client_id: str, table_no: int, body: BillRequest):
    bill = generate_bill(
        client_id, table_no,
        body.customer_name, body.customer_phone,
        body.tax_percent, body.discount, body.payment_mode,
    )
    if not bill:
        raise HTTPException(
            status_code=404,
            detail="No billable orders found. Orders must be marked 'done' by kitchen before billing, and must not already be paid."
        )
    return bill


@router.get("/api/bill/{bill_id}")
async def api_get_bill(bill_id: int):
    bill = get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill
