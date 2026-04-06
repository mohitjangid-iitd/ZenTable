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
