import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles

from site_config import SITE_CONFIG
from database import get_db,init_db, seed_tables, get_all_restaurants_info, get_all_site_settings
from r2 import USE_R2, r2_public_url, IS_PROD
from helpers import get_client_data
from trash_utils import purge_expired_trash

from routers.menu import router as menu_router
from routers.tables import router as tables_router
from routers.orders import router as orders_router
from routers.login import router as login_router
from routers.admin import router as admin_router
from routers.pages import router as pages_router
from routers.owner import router as owner_router
from routers.chatbot import router as chatbot_router
from routers.help_chat import router as help_chat_router
from routers.image_to_menu import router as image_to_menu_router
from routers.blog import router as blog_router
from blog_db import init_blog_tables, get_published_posts as get_blog_posts
from templates_env import templates

# ════════════════════════════════
# LIFESPAN
# ════════════════════════════════

@asynccontextmanager
async def lifespan(app):
    init_db()
    init_blog_tables()
    purge_expired_trash()
    for r in get_all_restaurants_info():
        rdata = get_client_data(r["client_id"])
        if rdata and "num_tables" in rdata.get("restaurant", {}):
            # Saari branches ke liye seed karo
            from database import get_restaurant_branches
            branches = get_restaurant_branches(r["client_id"])
            for branch in branches:
                branch_config = branch["config"] if isinstance(branch["config"], dict) else {}
                num = branch_config.get("restaurant", {}).get("num_tables") \
                      or rdata["restaurant"]["num_tables"]
                seed_tables(r["client_id"], num, branch["branch_id"])
    templates.env.globals["static_v"] = lambda path: \
        int(os.path.getmtime(f"static/{path}")) if os.path.exists(f"static/{path}") else 0
    templates.env.globals["site"] = SITE_CONFIG
    templates.env.globals["site_settings"] = get_all_site_settings()
    yield

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

# ════════════════════════════════
# STATIC FILES
# ════════════════════════════════

app.mount("/static", StaticFiles(directory="static"), name="static")

ALLOWED_EXTENSIONS   = {".glb", ".mind", ".png", ".jpg", ".jpeg", ".webp"}
PROTECTED_EXTENSIONS = {".glb"}

@app.get("/static/assets/{client_id}/{filename}")
async def serve_asset(request: Request, client_id: str, filename: str):
    if ".." in client_id or ".." in filename or "/" in filename:
        raise HTTPException(status_code=403, detail="Forbidden")
    ext = os.path.splitext(filename)[1].lower()
    if ext in PROTECTED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="Use signed URL")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="File type not allowed")
    if not get_client_data(client_id):
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if USE_R2:
        return RedirectResponse(url=r2_public_url(f"{client_id}/{filename}"), status_code=302)
    file_path = f"static/assets/{client_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path)

# ════════════════════════════════
# UTILITY ROUTES
# ════════════════════════════════


@app.api_route("/ping", methods=["GET", "HEAD"])
def ping(response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    try:
        conn = get_db()
        cur = conn.cursor()

        # Neon wake-up query
        cur.execute("SELECT 1;")
        cur.fetchone()

        cur.close()
        conn.close()

        return {"status": "ok"}

    except Exception as e:
        # monitor ko failure dikhega
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/google67ff8e4e4bb9c2ef.html")
def verify():
    return FileResponse("Public_HTML/google67ff8e4e4bb9c2ef.html")

@app.get("/sitemap.xml")
async def sitemap(request: Request):
    base_url = str(request.base_url).rstrip("/")
    urls     = [f"{base_url}/"]
    try:
        for r in get_all_restaurants_info():
            rdata = get_client_data(r["client_id"])
            if not rdata or not rdata.get("subscription", {}).get("active", True):
                continue
            cid = r["client_id"]
            urls.append(f"{base_url}/{cid}")
            urls.append(f"{base_url}/{cid}/menu")
            if "ar_menu" in rdata.get("subscription", {}).get("features", []):
                urls.append(f"{base_url}/{cid}/ar-menu")
        for post in get_blog_posts(limit=200):
            urls.append(f"{base_url}/blog/{post['slug']}")
    except Exception as e:
        print(f"Sitemap error: {e}")
    xml  = '<?xml version="1.0" encoding="UTF-8"?>'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for url in urls:
        xml += f"<url><loc>{url}</loc></url>"
    xml += "</urlset>"
    return Response(content=xml, media_type="application/xml")

@app.get("/")
async def landing(request: Request):
    if IS_PROD and request.headers.get("host") == "admin.zentable.in":
        auth_token = request.cookies.get("auth_token")
        from helpers import get_current_user
        user = get_current_user(auth_token)
        if user and user.get("role") == "admin":
            return templates.TemplateResponse("admin.html", {
                "request": request, "site": SITE_CONFIG, "user": user,
            })
        return templates.TemplateResponse("admin_login.html", {
            "request": request, "site": SITE_CONFIG,
        })
    return templates.TemplateResponse("landing.html", {
        "request": request, "config": SITE_CONFIG
    })

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    return {}

# ── Routers — pages LAST (wildcard /{client_id} routes) ──
app.include_router(menu_router)
app.include_router(tables_router)
app.include_router(orders_router)
app.include_router(login_router)
app.include_router(admin_router)
app.include_router(owner_router)
app.include_router(chatbot_router)
app.include_router(help_chat_router)
app.include_router(image_to_menu_router)
app.include_router(blog_router)
app.include_router(pages_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
