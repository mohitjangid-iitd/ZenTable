"""
routers/menu.py — Menu API + GLB file serving

GET /api/menu/{client_id}  — signed GLB URLs ke saath menu data
GET /glb/{token}           — signed token se GLB file serve
"""

import copy
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse

from helpers import get_client_data
from glb_token import GLB_TOKEN_EXPIRY, create_glb_token, verify_glb_token
from r2 import USE_R2, r2_presign

router = APIRouter()


@router.get("/api/menu/{client_id}")
async def get_menu_api(client_id: str):
    data = get_client_data(client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")

    safe_data = copy.deepcopy(data)
    for item in safe_data.get("items", []):
        model = item.get("model")
        if model and model.lower() != "none":
            token = create_glb_token(client_id, model)
            item["model_url"] = f"/glb/{token}"
        else:
            item["model_url"] = None
    return JSONResponse(content=safe_data)


@router.get("/glb/{token}")
async def serve_glb(token: str):
    """Signed token se GLB file serve karo"""
    result = verify_glb_token(token)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    client_id, filepath = result

    if USE_R2:
        presigned = r2_presign(filepath, expires=GLB_TOKEN_EXPIRY)
        return RedirectResponse(url=presigned, status_code=302)

    file_path = f"private/assets/{filepath}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model not found")
    return FileResponse(
        file_path,
        media_type="model/gltf-binary",
        headers={
            "Cache-Control": "no-store, no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        }
    )
