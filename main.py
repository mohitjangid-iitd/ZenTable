import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles

from site_config import SITE_CONFIG
from db import get_db, init_all, seed_tables, get_all_restaurants_info, get_all_site_settings
from r2 import USE_R2, r2_public_url, IS_PROD
from helpers import get_client_data, is_restaurant_active, has_feature
from trash_utils import purge_expired_trash
from rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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
from routers.billing import router as billing_router
from routers.customer_auth import router as customer_auth_router
from db.blog_db import get_published_posts as get_blog_posts
from db.billing_db import sync_plan_features, run_daily_billing_cron, get_all_plans, get_all_addons
from templates_env import templates

# ════════════════════════════════
# LIFESPAN
# ════════════════════════════════

@asynccontextmanager
async def lifespan(app):
    init_all()
    sync_plan_features()
    purge_expired_trash()
    for r in get_all_restaurants_info():
        rdata = get_client_data(r["client_id"])
        if rdata and "num_tables" in rdata.get("restaurant", {}):
            # Saari branches ke liye seed karo
            from db import get_restaurant_branches
            branches = get_restaurant_branches(r["client_id"])
            for branch in branches:
                branch_config = branch["config"] if isinstance(branch["config"], dict) else {}
                num = branch_config.get("restaurant", {}).get("num_tables") \
                      or rdata["restaurant"]["num_tables"]
                seed_tables(r["client_id"], num, branch["branch_id"])
    import json as _json
    templates.env.globals["static_v"] = lambda path: \
        int(os.path.getmtime(f"static/{path}")) if os.path.exists(f"static/{path}") else 0
    templates.env.globals["site"] = SITE_CONFIG
    _ss = get_all_site_settings()
    templates.env.globals["site_settings"] = _ss
    # fromjson filter — template mein use kar sakte hain
    templates.env.filters["fromjson"] = lambda s: _json.loads(s) if isinstance(s, str) else s
    # billing_plans — landing page pricing ke liye (live fetch)
    try:
        templates.env.globals["billing_plans"] = get_all_plans()
        templates.env.globals["billing_addons"] = get_all_addons()
    except Exception:
        templates.env.globals["billing_plans"] = []
        templates.env.globals["billing_addons"] = []

    run_daily_billing_cron()

    yield

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

# ── Rate limiting ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
        if request.query_params.get("proxy") == "1":
            import httpx
            async with httpx.AsyncClient() as client:
                r2_url = r2_public_url(f"{client_id}/{filename}")
                try:
                    r = await client.get(r2_url)
                    if r.status_code == 200:
                        media_type = "image/png"
                        if ext in (".jpg", ".jpeg"):
                            media_type = "image/jpeg"
                        elif ext == ".webp":
                            media_type = "image/webp"
                        return Response(content=r.content, media_type=media_type)
                except Exception as e:
                    print(f"Error proxying asset: {e}")
        return RedirectResponse(url=r2_public_url(f"{client_id}/{filename}"), status_code=302)
    file_path = f"static/assets/{client_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file_path)

# ════════════════════════════════
# UTILITY ROUTES
# ════════════════════════════════


@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return {"status": "ok"}

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
            if not rdata or not is_restaurant_active(r["client_id"]):
                continue
            cid = r["client_id"]
            urls.append(f"{base_url}/{cid}")
            urls.append(f"{base_url}/{cid}/menu")
            if has_feature(r["client_id"], "ar_menu"):
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
        "request": request, "config": SITE_CONFIG,
        "billing_plans": get_all_plans(),
        "billing_addons": get_all_addons(),
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
app.include_router(billing_router)
app.include_router(customer_auth_router)
app.include_router(pages_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
