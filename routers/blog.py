"""
routers/blog.py — Blog system routes

Public routes:
  GET  /blog                    → published posts listing
  GET  /blog/rss.xml            → RSS feed feed generator
  GET  /blog/{slug}             → single post reader
  GET  /blog/tag/{tag}          → tag filter page

Auth routes (management):
  GET  /{client_id}/staff/blog  → blogger's management page
  GET  /admin/blog              → admin blog management (sabhi posts)

Editor routes (auth):
  GET  /blog/editor             → new post editor
  GET  /blog/editor/{id}        → edit existing post

API routes:
  POST /api/blog/create         → naya post create/save as draft
  POST /api/blog/update/{id}    → existing post update
  POST /api/blog/submit/{id}    → submit for review (blogger/owner)
  POST /api/blog/publish/{id}   → publish (admin only)
  POST /api/blog/reject/{id}    → reject with note (admin only)
  POST /api/blog/archive/{id}   → archive (admin only)
  POST /api/blog/unarchive/{id} → unarchive (admin only)
  DELETE /api/blog/{id}         → hard delete (admin only)
"""

import os
import re
import uuid
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional

from r2 import USE_R2, r2_upload, r2_delete, r2_public_url, R2_PUBLIC_URL
from helpers import get_current_user, get_client_data, has_feature
from db import get_site_setting
from templates_env import templates
from db.blog_db import (
    create_blog_post, update_blog_post,
    submit_for_review, publish_post, reject_post,
    archive_post, unarchive_post, delete_post,
    get_post_by_id, get_post_by_slug,
    get_posts, get_pending_review_posts,
    get_published_posts, get_posts_by_tag,
    count_posts, count_posts_by_tag, generate_unique_slug, slug_exists,
)

router = APIRouter()


# ════════════════════════════════
# HELPERS
# ════════════════════════════════

def _get_user(request: Request) -> dict | None:
    token = request.cookies.get("auth_token")
    return get_current_user(token)

def _require_blog_access(request: Request):
    """admin | owner | blogger — warna 401"""
    user = _get_user(request)
    if not user or user.get("role") not in ("admin", "owner", "blogger"):
        raise HTTPException(status_code=401, detail="Login required")
    return user

def _require_admin(request: Request):
    user = _get_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

def _title_to_slug(title: str) -> str:
    """'My Great Post!' → 'my-great-post'"""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)      # special chars hata do
    slug = re.sub(r"[\s_]+", "-", slug)        # spaces → hyphens
    slug = re.sub(r"-+", "-", slug).strip("-") # multiple hyphens clean karo
    return slug or "post"

def _can_edit(user: dict, post: dict) -> bool:
    """
    Kya ye user is post ko edit kar sakta hai?
    - admin: sab
    - owner: apne client_id ke posts
    - blogger: sirf apne posts (author_id match)
    """
    role = user.get("role")
    if role == "admin":
        return True
    if role == "owner":
        return post.get("client_id") == user.get("restaurant_id") or \
               post.get("client_id") == user.get("client_id")
    if role == "blogger":
        return post.get("author_id") == user.get("staff_id")
    return False


def delete_blog_image(image_url_or_path: Optional[str]):
    """
    Blog image ko local static/blog aur Cloudflare R2 dono se safely delete karta hai.
    External URLs (jaise Unsplash) ko touch nahi karta.
    """
    if not image_url_or_path or not isinstance(image_url_or_path, str):
        return

    # Blog filename extract karo
    filename = None
    if "/static/blog/" in image_url_or_path:
        filename = image_url_or_path.split("/static/blog/")[-1]
    elif "static/blog/" in image_url_or_path:
        filename = image_url_or_path.split("static/blog/")[-1]
    elif "/blog/" in image_url_or_path:
        filename = image_url_or_path.split("/blog/")[-1]
    elif image_url_or_path.startswith("blog/"):
        filename = image_url_or_path[len("blog/"):]

    if not filename:
        return

    # Query string ya fragments strip karo
    filename = filename.split("?")[0].split("#")[0].strip()
    # Path traversal safety check
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return

    # 1. Local static/blog se delete karo
    local_path = os.path.join("static", "blog", filename)
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"[BLOG] Deleted local image: {local_path}")
    except Exception as e:
        print(f"Error removing local blog image {local_path}: {e}")

    # 2. Cloudflare R2 se delete karo
    try:
        if USE_R2:
            r2_delete(f"blog/{filename}")
            print(f"[BLOG] Deleted R2 image: blog/{filename}")
    except Exception as e:
        print(f"Error removing R2 blog image blog/{filename}: {e}")


# ════════════════════════════════
# PUBLIC ROUTES
# ════════════════════════════════

@router.get("/blog", response_class=HTMLResponse)
async def blog_public_list(request: Request, page: int = 1):
    limit  = 12
    offset = (page - 1) * limit
    posts  = get_published_posts(limit=limit, offset=offset)
    total  = count_posts(status="published")
    return templates.TemplateResponse("blog_public_list.html", {
        "request": request,
        "posts":   posts,
        "page":    page,
        "total":   total,
        "limit":   limit,
    })


@router.get("/blog/rss.xml")
async def blog_rss(request: Request):
    base_url = str(request.base_url).rstrip("/")
    posts    = get_published_posts(limit=50)

    items = ""
    for post in posts:
        pub_date = post.get("published_at") or post.get("created_at") or ""
        # RSS date format — basic ISO string theek hai most readers ke liye
        link = f"{base_url}/blog/{post['slug']}"
        desc = post.get("meta_desc") or ""
        items += f"""
        <item>
            <title><![CDATA[{post['title']}]]></title>
            <link>{link}</link>
            <guid isPermaLink="true">{link}</guid>
            <description><![CDATA[{desc}]]></description>
            <author>{post.get('author_name', '')}</author>
            <pubDate>{pub_date}</pubDate>
        </item>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>ZenTable Blog</title>
        <link>{base_url}/blog</link>
        <description>Stories, guides and updates from ZenTable restaurants</description>
        <language>en-in</language>
        <atom:link href="{base_url}/blog/rss.xml" rel="self" type="application/rss+xml"/>
        {items}
    </channel>
</rss>"""

    from fastapi.responses import Response
    return Response(content=xml, media_type="application/rss+xml")


@router.get("/blog/tag/{tag}", response_class=HTMLResponse)
async def blog_tag_page(request: Request, tag: str, page: int = 1):
    limit  = 12
    offset = (page - 1) * limit
    posts  = get_posts_by_tag(tag, limit=limit, offset=offset)
    total  = count_posts_by_tag(tag)
    return templates.TemplateResponse("blog_public_list.html", {
        "request":    request,
        "posts":      posts,
        "active_tag": tag,
        "page":       page,
        "total":      total,
        "limit":      limit,
    })

# ════════════════════════════════
# MANAGEMENT PAGES (AUTH)
# ════════════════════════════════

@router.get("/blog/editor", response_class=HTMLResponse)
async def blog_editor_new(request: Request):
    user = _require_blog_access(request)
    role = user.get("role")

    # site settings check
    if role == "blogger" and not get_site_setting("blog_blogger_enabled", True):
        raise HTTPException(status_code=403, detail="Blog feature is currently disabled")
    if role == "owner" and not get_site_setting("blog_owner_enabled", True):
        raise HTTPException(status_code=403, detail="Blog feature is currently disabled")

    client_id = None
    if role == "owner":
        client_id = user.get("restaurant_id") or user.get("client_id")
    elif role == "blogger":
        client_id = user.get("client_id")

    return templates.TemplateResponse("blog_editor.html", {
        "request":   request,
        "user":      user,
        "post":      None,   # new post
        "client_id": client_id,
    })


@router.get("/blog/editor/{post_id}", response_class=HTMLResponse)
async def blog_editor_edit(request: Request, post_id: int):
    user = _require_blog_access(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not _can_edit(user, post):
        raise HTTPException(status_code=403, detail="Access denied")

    return templates.TemplateResponse("blog_editor.html", {
        "request": request,
        "user":    user,
        "post":    post,
    })

@router.get("/blog/preview/{post_id}", response_class=HTMLResponse)
async def blog_post_preview(request: Request, post_id: int):
    """Auth-gated preview — koi bhi status dikha sakta hai (draft, pending, published)"""
    user = _require_blog_access(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not _can_edit(user, post):
        raise HTTPException(status_code=403, detail="Access denied")

    restaurant = None
    if post.get("client_id"):
        rdata = get_client_data(post["client_id"])
        if rdata:
            restaurant = rdata.get("restaurant")

    return templates.TemplateResponse("blog_reader.html", {
        "request":    request,
        "post":       post,
        "restaurant": restaurant,
        "preview":    True,
        "user":       user,
    })


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_reader(request: Request, slug: str):
    # slug 'editor' ya 'preview' nahi hona chahiye — warna route conflict
    if slug in ("editor", "preview"):
        raise HTTPException(status_code=404)

    post = get_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # restaurant-specific post ke liye branding data
    restaurant = None
    if post.get("client_id"):
        rdata = get_client_data(post["client_id"])
        if rdata:
            restaurant = rdata.get("restaurant")

    return templates.TemplateResponse("blog_reader.html", {
        "request":    request,
        "post":       post,
        "restaurant": restaurant,
    })

@router.get("/{client_id}/staff/blog", response_class=HTMLResponse)
async def blogger_management(request: Request, client_id: str):
    """Blogger ka management page — sirf apne posts"""
    user = _get_user(request)
    if not user or user.get("role") not in ("blogger", "owner", "admin"):
        return RedirectResponse(url=f"/login?next=/{client_id}/staff/blog")

    role = user.get("role")

    # Feature gate — blog feature check (admin always allowed)
    if role != "admin" and not has_feature(client_id, "blog"):
        raise HTTPException(status_code=403, detail="Blog feature not available in your plan")

    # site settings check
    if role == "blogger" and not get_site_setting("blog_blogger_enabled", True):
        raise HTTPException(status_code=403, detail="Blog feature is currently disabled")
    if role == "owner" and not get_site_setting("blog_owner_enabled", True):
        raise HTTPException(status_code=403, detail="Blog feature is currently disabled")

    # blogger sirf apne client_id ke page pe ja sakta hai
    if role == "blogger" and user.get("client_id") != client_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # owner sirf apne restaurant ka page dekh sakta hai
    if role == "owner":
        owner_cid = user.get("restaurant_id") or user.get("client_id")
        if owner_cid != client_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # posts fetch — role ke hisaab se filter
    if role == "blogger":
        posts = get_posts(client_id=client_id, author_id=user.get("staff_id"))
    else:
        # owner ya admin — is client_id ke saare posts
        posts = get_posts(client_id=client_id)

    pending = get_pending_review_posts(client_id=client_id)

    return templates.TemplateResponse("blog_list.html", {
        "request":   request,
        "user":      user,
        "posts":     posts,
        "pending":   pending,
        "client_id": client_id,
        "view":      "restaurant",   # template ko pata chale ki kaunsa view hai
    })


@router.get("/admin/blog", response_class=HTMLResponse)
async def admin_blog_management(request: Request, status: str = None):
    """Admin blog panel — sabhi restaurants ke posts"""
    user = _require_admin(request)

    posts   = get_posts(status=status if status else None)
    pending = get_pending_review_posts()

    return templates.TemplateResponse("blog_list.html", {
        "request":      request,
        "user":         user,
        "posts":        posts,
        "pending":      pending,
        "active_status": status,
        "view":         "admin",
    })


# ════════════════════════════════
# API — CREATE / UPDATE
# ════════════════════════════════

class PostSaveBody(BaseModel):
    title:        str
    content:      str
    slug:         Optional[str] = None
    tags:         Optional[list] = []
    cover_image:  Optional[str] = None
    meta_desc:    Optional[str] = None
    client_id:    Optional[str] = None   # override — admin ke liye
    line_spacing: Optional[str] = '1.7'

class PostUpdateBody(BaseModel):
    title:        Optional[str] = None
    content:      Optional[str] = None
    slug:         Optional[str] = None
    tags:         Optional[list] = None
    cover_image:  Optional[str] = None
    meta_desc:    Optional[str] = None
    line_spacing: Optional[str] = None

class RejectBody(BaseModel):
    note: str


@router.post("/api/blog/create")
async def api_create_post(request: Request, body: PostSaveBody):
    user = _require_blog_access(request)
    role = user.get("role")

    # client_id resolve
    client_id = body.client_id  # admin override
    if not client_id:
        if role in ("owner", "blogger"):
            client_id = user.get("restaurant_id") or user.get("client_id")

    # slug generate karo agar nahi diya
    base_slug = _title_to_slug(body.slug or body.title)
    slug = generate_unique_slug(base_slug)

    # author info
    author_type = role
    author_id   = user.get("admin_id") or user.get("owner_id") or user.get("staff_id")
    author_name = user.get("name", "")

    post_id = create_blog_post(
        title        = body.title,
        content      = body.content,
        author_id    = author_id,
        author_type  = author_type,
        author_name  = author_name,
        slug         = slug,
        client_id    = client_id,
        tags         = body.tags,
        cover_image  = (body.cover_image.strip() or None) if body.cover_image else None,
        meta_desc    = body.meta_desc,
        line_spacing = body.line_spacing or '1.7',
        status       = "draft",
    )
    return JSONResponse({"success": True, "post_id": post_id, "slug": slug})


@router.post("/api/blog/update/{post_id}")
async def api_update_post(request: Request, post_id: int, body: PostUpdateBody):
    user = _require_blog_access(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404)
    if not _can_edit(user, post):
        raise HTTPException(status_code=403)

    # slug change hone pe uniqueness check
    if body.slug and body.slug != post["slug"]:
        if slug_exists(body.slug):
            raise HTTPException(status_code=409, detail="Slug already taken")

    # Cover image replace ya remove hone pe purani photo dono jagah (R2 & local) se delete karo
    if body.cover_image is not None:
        new_cover = body.cover_image.strip() or None
        old_cover = post.get("cover_image")
        if old_cover and old_cover != new_cover:
            delete_blog_image(old_cover)

    update_blog_post(
        post_id,
        title        = body.title,
        content      = body.content,
        slug         = body.slug,
        tags         = body.tags,
        cover_image  = body.cover_image,
        meta_desc    = body.meta_desc,
        line_spacing = body.line_spacing,
    )
    return JSONResponse({"success": True})


# ════════════════════════════════
# API — IMAGE UPLOAD & CLEANUP
# ════════════════════════════════

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_BLOG_IMAGE_SIZE = 15 * 1024 * 1024  # 15 MB

@router.post("/api/blog/upload-image")
async def api_upload_blog_image(request: Request, file: UploadFile = File(...)):
    """
    Blog cover image ya editor internal images upload endpoint.
    - Prod me (USE_R2=True): Cloudflare R2 me 'blog/{filename}'
    - Local me (USE_R2=False): Local 'static/blog/{filename}'
    """
    _require_blog_access(request)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    contents = await file.read()
    if len(contents) > MAX_BLOG_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds limit (max 15MB)")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    raw_name = os.path.basename(file.filename or "image.jpg")
    clean_name = re.sub(r"[^\w\-.]", "_", raw_name)
    safe_name = f"blog_{uuid.uuid4().hex[:10]}_{clean_name}"

    if USE_R2:
        r2_upload(contents, f"blog/{safe_name}", safe_name)
        url = r2_public_url(f"blog/{safe_name}")
    else:
        save_dir = os.path.join("static", "blog")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, safe_name)
        with open(save_path, "wb") as f:
            f.write(contents)
        url = f"/static/blog/{safe_name}"

    return JSONResponse({
        "success": True,
        "url": url,
        "filename": safe_name
    })


class DeleteImageBody(BaseModel):
    url: str

@router.post("/api/blog/delete-image")
async def api_delete_blog_image(request: Request, body: DeleteImageBody):
    """Uploaded image discard / remove hone pe storage cleanup"""
    _require_blog_access(request)
    if body.url:
        delete_blog_image(body.url)
    return JSONResponse({"success": True})


# ════════════════════════════════
# API — STATUS TRANSITIONS
# ════════════════════════════════

@router.post("/api/blog/submit/{post_id}")
async def api_submit_review(request: Request, post_id: int):
    user = _require_blog_access(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404)
    if not _can_edit(user, post):
        raise HTTPException(status_code=403)
    if post["status"] != "draft":
        raise HTTPException(status_code=400, detail="Sirf draft posts submit ho sakte hain")
    submit_for_review(post_id)
    return JSONResponse({"success": True})


@router.post("/api/blog/publish/{post_id}")
async def api_publish_post(request: Request, post_id: int):
    _require_admin(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404)
    publish_post(post_id)
    return JSONResponse({"success": True, "slug": post["slug"]})


@router.post("/api/blog/reject/{post_id}")
async def api_reject_post(request: Request, post_id: int, body: RejectBody):
    _require_admin(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404)
    reject_post(post_id, body.note)
    return JSONResponse({"success": True})


@router.post("/api/blog/archive/{post_id}")
async def api_archive_post(request: Request, post_id: int):
    _require_admin(request)
    archive_post(post_id)
    return JSONResponse({"success": True})


@router.post("/api/blog/unarchive/{post_id}")
async def api_unarchive_post(request: Request, post_id: int):
    _require_admin(request)
    unarchive_post(post_id)
    return JSONResponse({"success": True})


@router.delete("/api/blog/{post_id}")
async def api_delete_post(request: Request, post_id: int):
    _require_admin(request)
    post = get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # Post delete hone par cover image dono jagah se delete karo
    if post.get("cover_image"):
        delete_blog_image(post["cover_image"])
    delete_post(post_id)
    return JSONResponse({"success": True})
