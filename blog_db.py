"""
blog_db.py — Blog system ke liye standalone DB functions
Baad mein database.py mein merge hoga jab sab pakka ho jaye.

Tables:
  - blog_posts  — main posts table
"""

import json
from datetime import datetime
from database import get_db   # existing pool reuse karo


# ════════════════════════════════
# TABLE INIT
# ════════════════════════════════

def init_blog_tables():
    """
    Blog tables create karo — main.py ke lifespan mein init_db() ke baad call karo.
    Safe to call multiple times (IF NOT EXISTS).
    """
    conn = get_db()
    cur = conn._conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blog_posts (
            id           SERIAL PRIMARY KEY,
            slug         TEXT UNIQUE NOT NULL,
            title        TEXT NOT NULL,
            content      TEXT NOT NULL,           -- HTML (rich text editor output)
            author_id    INTEGER,                 -- admins.id ya staff.id
            author_type  TEXT,                    -- 'admin' | 'owner' | 'blogger'
            author_name  TEXT,                    -- display name (denormalized for speed)
            client_id    TEXT,                    -- NULL = ZenTable post, else restaurant-specific
            status       TEXT DEFAULT 'draft',    -- draft | pending_review | published | archived
            tags         TEXT DEFAULT '[]',       -- JSON array (TEXT — pg array se zyada portable)
            cover_image  TEXT,                    -- R2 URL ya local path
            meta_desc    TEXT,                    -- SEO meta description (160 chars max)
            reject_note  TEXT,                    -- admin ka rejection comment
            created_at   TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
            published_at TEXT,
            updated_at   TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Blog tables initialized")


# ════════════════════════════════
# HELPERS
# ════════════════════════════════

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _row(row) -> dict | None:
    if not row:
        return None
    d = dict(row)
    # tags JSON string → Python list
    try:
        d["tags"] = json.loads(d.get("tags") or "[]")
    except Exception:
        d["tags"] = []
    return d


# ════════════════════════════════
# CREATE / SAVE
# ════════════════════════════════

def create_blog_post(
    title: str,
    content: str,
    author_id: int,
    author_type: str,        # 'admin' | 'owner' | 'blogger'
    author_name: str,
    slug: str,
    client_id: str = None,   # None = ZenTable-level post
    tags: list = None,
    cover_image: str = None,
    meta_desc: str = None,
    status: str = "draft",   # admin seedha 'published' bhi de sakta hai
) -> int:
    """
    Naya blog post create karo.
    Returns: new post id
    """
    now = _now()
    published_at = now if status == "published" else None

    conn = get_db()
    import psycopg2.extras
    cur = conn._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO blog_posts
            (title, content, author_id, author_type, author_name,
             slug, client_id, tags, cover_image, meta_desc,
             status, published_at, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        title, content, author_id, author_type, author_name,
        slug, client_id,
        json.dumps(tags or []),
        cover_image, meta_desc,
        status, published_at, now, now
    ))
    post_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()
    return post_id


def update_blog_post(
    post_id: int,
    title: str = None,
    content: str = None,
    slug: str = None,
    tags: list = None,
    cover_image: str = None,
    meta_desc: str = None,
) -> bool:
    """
    Draft/existing post update karo — sirf diye gaye fields update honge.
    Status change ke liye alag functions hain (submit_for_review, publish, etc.)
    """
    fields = []
    params = []

    if title       is not None: fields.append("title=%s");        params.append(title)
    if content     is not None: fields.append("content=%s");      params.append(content)
    if slug        is not None: fields.append("slug=%s");         params.append(slug)
    if tags        is not None: fields.append("tags=%s");         params.append(json.dumps(tags))
    if cover_image is not None: fields.append("cover_image=%s");  params.append(cover_image)
    if meta_desc   is not None: fields.append("meta_desc=%s");    params.append(meta_desc)

    if not fields:
        return False

    fields.append("updated_at=%s")
    params.append(_now())
    params.append(post_id)

    conn = get_db()
    conn.execute(
        f"UPDATE blog_posts SET {', '.join(fields)} WHERE id=%s",
        params
    )
    conn.commit()
    conn.close()
    return True


# ════════════════════════════════
# STATUS TRANSITIONS
# ════════════════════════════════

def submit_for_review(post_id: int) -> bool:
    """Blogger/owner → admin ke review ke liye submit karo (draft → pending_review)"""
    conn = get_db()
    conn.execute("""
        UPDATE blog_posts
        SET status='pending_review', updated_at=%s
        WHERE id=%s AND status='draft'
    """, (_now(), post_id))
    conn.commit()
    conn.close()
    return True

def publish_post(post_id: int) -> bool:
    """Admin → post publish karo (any status → published)"""
    now = _now()
    conn = get_db()
    conn.execute("""
        UPDATE blog_posts
        SET status='published', published_at=%s, updated_at=%s, reject_note=NULL
        WHERE id=%s
    """, (now, now, post_id))
    conn.commit()
    conn.close()
    return True

def reject_post(post_id: int, note: str) -> bool:
    """Admin → post reject karo, blogger ko reason batao (pending_review → draft)"""
    conn = get_db()
    conn.execute("""
        UPDATE blog_posts
        SET status='draft', reject_note=%s, updated_at=%s
        WHERE id=%s
    """, (note, _now(), post_id))
    conn.commit()
    conn.close()
    return True

def archive_post(post_id: int) -> bool:
    """Admin → post archive karo (published → archived)"""
    conn = get_db()
    conn.execute("""
        UPDATE blog_posts
        SET status='archived', updated_at=%s
        WHERE id=%s
    """, (_now(), post_id))
    conn.commit()
    conn.close()
    return True

def unarchive_post(post_id: int) -> bool:
    """Admin → archived post wapas published karo"""
    conn = get_db()
    conn.execute("""
        UPDATE blog_posts
        SET status='published', updated_at=%s
        WHERE id=%s AND status='archived'
    """, (_now(), post_id))
    conn.commit()
    conn.close()
    return True


# ════════════════════════════════
# DELETE
# ════════════════════════════════

def delete_post(post_id: int) -> bool:
    """Admin only — hard delete"""
    conn = get_db()
    conn.execute("DELETE FROM blog_posts WHERE id=%s", (post_id,))
    conn.commit()
    conn.close()
    return True


# ════════════════════════════════
# FETCH — SINGLE POST
# ════════════════════════════════

def get_post_by_id(post_id: int) -> dict | None:
    conn = get_db()
    cur = conn.execute("SELECT * FROM blog_posts WHERE id=%s", (post_id,))
    row = cur.fetchone()
    conn.close()
    return _row(row)

def get_post_by_slug(slug: str) -> dict | None:
    """Public reader ke liye — published posts only"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM blog_posts WHERE slug=%s AND status='published'", (slug,)
    )
    row = cur.fetchone()
    conn.close()
    return _row(row)


# ════════════════════════════════
# FETCH — LISTS
# ════════════════════════════════

def get_posts(
    client_id: str = None,     # None = saare, string = specific restaurant
    status: str = None,        # None = saare statuses
    author_id: int = None,     # sirf is author ke posts
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """
    Flexible post listing:
    - Admin: client_id=None, status=None  → sabhi posts
    - Owner: client_id='xyz'              → apne restaurant ke posts
    - Blogger: author_id=123             → sirf apne posts
    - Public list: status='published'    → sab published
    """
    query = "SELECT * FROM blog_posts WHERE 1=1"
    params = []

    if client_id is not None:
        query += " AND client_id=%s"
        params.append(client_id)
    if status is not None:
        query += " AND status=%s"
        params.append(status)
    if author_id is not None:
        query += " AND author_id=%s"
        params.append(author_id)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params += [limit, offset]

    conn = get_db()
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [_row(r) for r in rows]


def get_pending_review_posts(client_id: str = None) -> list[dict]:
    """
    Admin review panel ke liye — pending_review status wale posts.
    client_id dene pe sirf us restaurant ke posts.
    """
    return get_posts(client_id=client_id, status="pending_review")


def get_published_posts(client_id: str = None, limit: int = 20, offset: int = 0) -> list[dict]:
    """Public blog listing ke liye"""
    return get_posts(client_id=client_id, status="published", limit=limit, offset=offset)


def count_posts_by_tag(tag: str) -> int:
    """Tag page pagination ke liye total count"""
    conn = get_db()
    cur = conn._conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE status='published' AND tags LIKE %s",
        (f'%"{tag}"%',)
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def get_posts_by_tag(tag: str, limit: int = 20, offset: int = 0) -> list[dict]:
    """Tag filter — JSON array mein search (LIKE se kaam chalao abhi)"""
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM blog_posts
        WHERE status='published' AND tags LIKE %s
        ORDER BY published_at DESC
        LIMIT %s OFFSET %s
    """, (f'%"{tag}"%', limit, offset))
    rows = cur.fetchall()
    conn.close()
    return [_row(r) for r in rows]


def count_posts(client_id: str = None, status: str = None) -> int:
    """Pagination ke liye total count"""
    query = "SELECT COUNT(*) FROM blog_posts WHERE 1=1"
    params = []
    if client_id is not None:
        query += " AND client_id=%s"
        params.append(client_id)
    if status is not None:
        query += " AND status=%s"
        params.append(status)

    conn = get_db()
    cur = conn._conn.cursor()
    cur.execute(query, params)
    count = cur.fetchone()[0]
    conn.close()
    return count


# ════════════════════════════════
# SLUG UTILS
# ════════════════════════════════

def slug_exists(slug: str) -> bool:
    conn = get_db()
    cur = conn.execute("SELECT id FROM blog_posts WHERE slug=%s", (slug,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def generate_unique_slug(base_slug: str) -> str:
    """
    base_slug se unique slug banao.
    'my-post' already exists → 'my-post-2', 'my-post-3', etc.
    """
    slug = base_slug
    counter = 2
    while slug_exists(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
