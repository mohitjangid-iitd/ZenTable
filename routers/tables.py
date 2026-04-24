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
from fastapi import APIRouter, HTTPException, Cookie, Query

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
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    branch_id = user["branch_id"] or "__default__"
    activate_table(client_id, table_no, branch_id)
    return {"message": f"Table {table_no} activated"}


@router.post("/api/table/{client_id}/activate-all")
async def api_activate_all_tables(client_id: str,
                                   branch_id: Optional[str] = Query(None),
                                   auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    effective_branch = branch_id or user.get("branch_id") or "__default__"
    activate_all_tables(client_id, effective_branch)
    return {"message": "All tables activated"}


@router.post("/api/table/{client_id}/{table_no}/close")
async def api_close_table(client_id: str, table_no: int,
                           auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    branch_id = user["branch_id"] or "__default__"
    close_table(client_id, table_no, branch_id)
    return {"message": f"Table {table_no} closed"}


@router.post("/api/table/{client_id}/close-all")
async def api_close_all_tables(client_id: str,
                                branch_id: Optional[str] = Query(None),
                                auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["counter", "owner", "admin"], client_id)
    effective_branch = branch_id or user.get("branch_id") or "__default__"
    close_all_tables(client_id, effective_branch)
    return {"message": "All tables closed"}


@router.get("/api/tables/{client_id}/summary")
async def api_table_summary(client_id: str,
                             branch_id: Optional[str] = Query(None),
                             auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    effective_branch = branch_id or user.get("branch_id") or "__default__"
    return get_table_summary(client_id, effective_branch)


@router.get("/api/tables/{client_id}")
async def api_get_tables(client_id: str,
                         branch_id: Optional[str] = Query(None),
                         auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    effective_branch = branch_id or user.get("branch_id") or "__default__"
    return get_all_tables(client_id, effective_branch)


@router.get("/api/table/{client_id}/{table_no}/detail")
async def api_table_detail(client_id: str, table_no: int,
                            auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    branch_id = user["branch_id"] or "__default__"
    return get_table_orders_detail(client_id, table_no, branch_id)


# ════════════════════════════════
# WAITER CALL ENDPOINTS
# ════════════════════════════════

@router.post("/api/table/{client_id}/{table_no}/call")
async def api_call_waiter(client_id: str, table_no: int,
                          branch_id: Optional[str] = "__default__"):
    """Customer ne bell dabaya — no auth (public endpoint)
    branch_id query param se aa sakta hai — default __default__
    """
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    create_waiter_call(client_id, table_no, branch_id)
    return {"message": f"Waiter called for table {table_no}"}


@router.post("/api/table/{client_id}/{table_no}/call/resolve")
async def api_resolve_call(client_id: str, table_no: int,
                           auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    branch_id = user["branch_id"] or "__default__"
    resolve_waiter_call(client_id, table_no, branch_id)
    return {"message": f"Call resolved for table {table_no}"}


@router.get("/api/tables/{client_id}/calls")
async def api_get_calls(client_id: str,
                        auth_token: Optional[str] = Cookie(None)):
    user = require_auth(auth_token, ["waiter", "counter", "owner", "admin"], client_id)
    branch_id = user["branch_id"] or "__default__"
    return get_active_calls(client_id, branch_id)
