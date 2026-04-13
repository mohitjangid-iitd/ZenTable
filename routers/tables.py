"""
routers/tables.py — Table management API

POST /api/table/{client_id}/{table_no}/activate
POST /api/table/{client_id}/activate-all
POST /api/table/{client_id}/{table_no}/close
POST /api/table/{client_id}/close-all
GET  /api/tables/{client_id}/summary
GET  /api/tables/{client_id}
GET  /api/table/{client_id}/{table_no}/detail
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie

from database import (
    activate_table, activate_all_tables,
    close_table, close_all_tables,
    get_all_tables, get_table_summary,
    get_table_orders_detail,
    create_waiter_call, get_active_calls, resolve_waiter_call,
)
from helpers import get_client_data, require_auth

router = APIRouter()


@router.post("/api/table/{client_id}/{table_no}/activate")
async def api_activate_table(client_id: str, table_no: int,
                              auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    activate_table(client_id, table_no)
    return {"message": f"Table {table_no} activated"}


@router.post("/api/table/{client_id}/activate-all")
async def api_activate_all_tables(client_id: str,
                                   auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    activate_all_tables(client_id)
    return {"message": "All tables activated"}


@router.post("/api/table/{client_id}/{table_no}/close")
async def api_close_table(client_id: str, table_no: int,
                           auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    close_table(client_id, table_no)
    return {"message": f"Table {table_no} closed"}


@router.post("/api/table/{client_id}/close-all")
async def api_close_all_tables(client_id: str,
                                auth_token: Optional[str] = Cookie(None)):
    require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    close_all_tables(client_id)
    return {"message": "All tables closed"}


@router.get("/api/tables/{client_id}/summary")
async def api_table_summary(client_id: str):
    return get_table_summary(client_id)


@router.get("/api/tables/{client_id}")
async def api_get_tables(client_id: str):
    return get_all_tables(client_id)


@router.get("/api/table/{client_id}/{table_no}/detail")
async def api_table_detail(client_id: str, table_no: int):
    return get_table_orders_detail(client_id, table_no)


# ════════════════════════════════
# WAITER CALL ENDPOINTS
# ════════════════════════════════

@router.post("/api/table/{client_id}/{table_no}/call")
async def api_call_waiter(client_id: str, table_no: int):
    """Customer ne bell dabaya — no auth (public endpoint)"""
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    create_waiter_call(client_id, table_no)
    return {"message": f"Waiter called for table {table_no}"}


@router.post("/api/table/{client_id}/{table_no}/call/resolve")
async def api_resolve_call(client_id: str, table_no: int,
                           auth_token: Optional[str] = Cookie(None)):
    """Waiter ne call attend kar li — call hata do"""
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    resolve_waiter_call(client_id, table_no)
    return {"message": f"Call resolved for table {table_no}"}


@router.get("/api/tables/{client_id}/calls")
async def api_get_calls(client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    """Saari active waiter calls — waiter panel polling ke liye"""
    require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    return get_active_calls(client_id)
