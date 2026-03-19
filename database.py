# DATABASE_URL format: postgresql://user:password@host:5432/dbname
# Example: postgresql://zentable:secret@localhost:5432/zentable_db
# Set this environment variable before running the app.

"""
database.py — PostgreSQL setup for dynamic data
Static data (menu, theme, restaurant info) → JSON files (unchanged)
Dynamic data (orders, bills, tables, staff) → PostgreSQL (this file)
"""

from dotenv import load_dotenv
load_dotenv()

import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")

# ThreadedConnectionPool — min 2, max 20 connections
# Adjust minconn/maxconn based on your server's pg_max_connections
_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=20,
    dsn=DATABASE_URL
)


class _PgConn:
    """
    Thin wrapper around a psycopg2 connection from the pool.
    Mimics the sqlite3 connection API used throughout the codebase:
      conn.execute(sql, params)  → returns cursor
      conn.commit()
      conn.close()              → returns connection to pool (does NOT close it)
    Row dicts are returned via RealDictCursor, just like sqlite3.Row.
    """

    def __init__(self):
        self._conn = _pool.getconn()
        self._conn.autocommit = False

    def execute(self, sql, params=()):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        _pool.putconn(self._conn)


def get_db():
    """Return a _PgConn wrapper — callers use it exactly like sqlite3 connection."""
    return _PgConn()


def init_db():
    conn = get_db()
    cur = conn._conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id          SERIAL PRIMARY KEY,
            client_id   TEXT NOT NULL,
            table_no    INTEGER NOT NULL,
            status      TEXT DEFAULT 'inactive',
            opened_at   TEXT,
            closed_at   TEXT,
            UNIQUE(client_id, table_no)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id             SERIAL PRIMARY KEY,
            client_id      TEXT NOT NULL,
            table_no       INTEGER NOT NULL,
            source         TEXT DEFAULT 'customer',
            customer_name  TEXT,
            customer_phone TEXT,
            items          TEXT NOT NULL,
            total          INTEGER NOT NULL,
            status         TEXT DEFAULT 'pending',
            ready_items    TEXT DEFAULT '[]',
            created_at     TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
            updated_at     TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id             SERIAL PRIMARY KEY,
            client_id      TEXT NOT NULL,
            table_no       INTEGER NOT NULL,
            order_ids      TEXT NOT NULL,
            customer_name  TEXT,
            customer_phone TEXT,
            subtotal       INTEGER NOT NULL,
            tax            INTEGER DEFAULT 0,
            discount       INTEGER DEFAULT 0,
            total          INTEGER NOT NULL,
            payment_status TEXT DEFAULT 'unpaid',
            payment_mode   TEXT,
            created_at     TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    # ── Staff table ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id            SERIAL PRIMARY KEY,
            restaurant_id TEXT NOT NULL,
            username      TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            name          TEXT NOT NULL,
            role          TEXT NOT NULL,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
            UNIQUE(restaurant_id, username)
        )
    """)

    # ── Branches table (multi-branch support) ──
    # Single-outlet restaurants ke liye branch_id = NULL rehta hai — koi change nahi
    cur.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            id          SERIAL PRIMARY KEY,
            client_id   TEXT NOT NULL,
            branch_id   TEXT NOT NULL,
            name        TEXT NOT NULL,
            address     TEXT,
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
            UNIQUE(client_id, branch_id)
        )
    """)

    # ── Admin table (site admins) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id            SERIAL PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name          TEXT NOT NULL,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    # ── Migrations for older DBs ──
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'customer'")
    except Exception:
        conn._conn.rollback()
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS ready_items TEXT DEFAULT '[]'")
    except Exception:
        conn._conn.rollback()

    # ── Multi-branch migrations (safe — NULL default, existing data untouched) ──
    # branch_id = NULL → single-outlet restaurant (legacy + new single outlets)
    # branch_id = "branch_1" etc → multi-branch restaurant
    try:
        cur.execute("ALTER TABLE tables ADD COLUMN IF NOT EXISTS branch_id TEXT DEFAULT NULL")
    except Exception:
        conn._conn.rollback()
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS branch_id TEXT DEFAULT NULL")
    except Exception:
        conn._conn.rollback()
    try:
        cur.execute("ALTER TABLE bills ADD COLUMN IF NOT EXISTS branch_id TEXT DEFAULT NULL")
    except Exception:
        conn._conn.rollback()
    # branch_ids = JSON list — ek staff multiple branches pe kaam kar sake
    # e.g. '["branch_1"]' or '["branch_1","branch_2"]' or '[]' (single-outlet)
    try:
        cur.execute("ALTER TABLE staff ADD COLUMN IF NOT EXISTS branch_ids TEXT DEFAULT '[]'")
    except Exception:
        conn._conn.rollback()

    conn.commit()
    conn.close()
    print("✅ Database initialized")


# ════════════════════════════════
# AUTH — STAFF
# ════════════════════════════════

def create_staff(restaurant_id: str, username: str, password: str, name: str, role: str):
    """Naya staff member banao — password hash karke store hoga"""
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO staff (restaurant_id, username, password_hash, name, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (restaurant_id, username, password_hash, name, role))
        conn.commit()
        return True
    except Exception:
        return False  # username already exists
    finally:
        conn.close()

def verify_staff(restaurant_id: str, username: str, password: str):
    """Staff login verify karo — match hone pe staff dict return karo"""
    import bcrypt
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM staff
        WHERE restaurant_id=%s AND LOWER(username)=LOWER(%s) AND is_active=1
    """, (restaurant_id, username))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    staff = dict(row)
    if bcrypt.checkpw(password.encode(), staff["password_hash"].encode()):
        return staff
    return None

def get_staff_list(restaurant_id: str):
    """Ek restaurant ke saare staff members"""
    conn = get_db()
    cur = conn.execute("""
        SELECT id, restaurant_id, username, name, role, is_active, created_at
        FROM staff WHERE restaurant_id=%s ORDER BY role, name
    """, (restaurant_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_staff_password(staff_id: int, new_password: str):
    import bcrypt
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    conn.execute("UPDATE staff SET password_hash=%s WHERE id=%s", (password_hash, staff_id))
    conn.commit()
    conn.close()

def toggle_staff_active(staff_id: int, is_active: bool):
    conn = get_db()
    conn.execute("UPDATE staff SET is_active=%s WHERE id=%s", (int(is_active), staff_id))
    conn.commit()
    conn.close()

def delete_staff(staff_id: int):
    conn = get_db()
    conn.execute("DELETE FROM staff WHERE id=%s", (staff_id,))
    conn.commit()
    conn.close()


# ════════════════════════════════
# AUTH — ADMIN
# ════════════════════════════════

def create_admin(username: str, password: str, name: str):
    """Site admin banao"""
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO admins (username, password_hash, name)
            VALUES (%s, %s, %s)
        """, (username, password_hash, name))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def verify_admin(username: str, password: str):
    import bcrypt
    conn = get_db()
    cur = conn.execute("""
        SELECT * FROM admins WHERE LOWER(username)=LOWER(%s) AND is_active=1
    """, (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    admin = dict(row)
    if bcrypt.checkpw(password.encode(), admin["password_hash"].encode()):
        admin["role"] = "admin"
        return admin
    return None


# ════════════════════════════════
# TABLE OPERATIONS
# ════════════════════════════════

def seed_tables(client_id: str, num_tables: int):
    conn = get_db()
    for i in range(1, num_tables + 1):
        conn.execute("""
            INSERT INTO tables (client_id, table_no, status)
            VALUES (%s, %s, 'inactive')
            ON CONFLICT (client_id, table_no) DO NOTHING
        """, (client_id, i))
    conn.execute("""
        DELETE FROM tables WHERE client_id=%s AND table_no > %s
    """, (client_id, num_tables))
    conn.commit()
    conn.close()

def activate_table(client_id: str, table_no: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("""
        INSERT INTO tables (client_id, table_no, status, opened_at)
        VALUES (%s, %s, 'active', %s)
        ON CONFLICT (client_id, table_no)
        DO UPDATE SET status='active', opened_at=%s, closed_at=NULL
    """, (client_id, table_no, now, now))
    conn.commit()
    conn.close()

def activate_all_tables(client_id: str):
    """Saari tables ek saath activate karo"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("""
        UPDATE tables SET status='active', opened_at=%s, closed_at=NULL
        WHERE client_id=%s
    """, (now, client_id))
    conn.commit()
    conn.close()

def close_table(client_id: str, table_no: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("""
        UPDATE tables SET status='inactive', closed_at=%s
        WHERE client_id=%s AND table_no=%s
    """, (now, client_id, table_no))
    conn.commit()
    conn.close()

def close_all_tables(client_id: str):
    """Saari tables ek saath close karo"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute("""
        UPDATE tables SET status='inactive', closed_at=%s
        WHERE client_id=%s
    """, (now, client_id))
    conn.commit()
    conn.close()

def get_table_status(client_id: str, table_no: int):
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM tables WHERE client_id=%s AND table_no=%s",
        (client_id, table_no)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_tables(client_id: str):
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM tables WHERE client_id=%s ORDER BY table_no", (client_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_table_summary(client_id: str):
    """
    Returns each table with computed display_status based on current session.
    display_status: inactive | active | occupied | ready | done | billed | paid
    """
    import json as _json
    conn = get_db()

    cur = conn.execute(
        "SELECT * FROM tables WHERE client_id=%s ORDER BY table_no", (client_id,)
    )
    tables = cur.fetchall()

    result = []
    for t in tables:
        t = dict(t)
        table_no = t["table_no"]

        opened_at = t.get("opened_at") or "1970-01-01 00:00:00"
        opened_at = opened_at.replace("T", " ").split(".")[0]

        cur2 = conn.execute("""
            SELECT id, status FROM orders
            WHERE client_id=%s AND table_no=%s AND status != 'cancelled'
            AND created_at >= %s
        """, (client_id, table_no, opened_at))
        orders = [dict(o) for o in cur2.fetchall()]

        cur3 = conn.execute("""
            SELECT id, payment_status, total FROM bills
            WHERE client_id=%s AND table_no=%s AND created_at >= %s
            ORDER BY created_at DESC LIMIT 1
        """, (client_id, table_no, opened_at))
        session_bill = cur3.fetchone()
        session_bill = dict(session_bill) if session_bill else None

        paid_order_ids = set()
        cur4 = conn.execute("""
            SELECT order_ids FROM bills
            WHERE client_id=%s AND table_no=%s AND payment_status='paid' AND created_at >= %s
        """, (client_id, table_no, opened_at))
        for pb in cur4.fetchall():
            paid_order_ids.update(_json.loads(pb["order_ids"]))

        unpaid_orders   = [o for o in orders if o["id"] not in paid_order_ids]
        unpaid_statuses = [o["status"] for o in unpaid_orders]

        if not orders:
            display = t["status"]
        elif session_bill and session_bill["payment_status"] == "paid" and not unpaid_orders:
            display = "paid"
        elif session_bill and session_bill["payment_status"] == "unpaid":
            display = "billed"
        elif "ready" in unpaid_statuses:
            display = "ready"
        elif unpaid_statuses and all(s == "done" for s in unpaid_statuses):
            display = "done"
        elif unpaid_statuses:
            display = "occupied"
        else:
            display = "paid"

        t["display_status"]   = display
        t["order_count"]      = len(orders)
        t["opened_at_norm"]   = opened_at
        t["bill_id"]          = session_bill["id"] if session_bill else None
        t["bill_total"]       = session_bill["total"] if session_bill else None
        t["payment_status"]   = session_bill["payment_status"] if session_bill else None
        t["unpaid_done_ids"]  = [o["id"] for o in unpaid_orders if o["status"] == "done"]

        if session_bill and session_bill["payment_status"] == "unpaid":
            try:
                cur5 = conn.execute(
                    "SELECT order_ids FROM bills WHERE id=%s", (session_bill["id"],)
                )
                billed_ids = _json.loads(cur5.fetchone()["order_ids"])
            except Exception:
                billed_ids = []
        else:
            billed_ids = []
        t["billed_order_ids"] = billed_ids

        # Paid today — current session ke paid order ids
        paid_today_ids = []
        try:
            today = __import__('datetime').date.today().isoformat()
            cur6 = conn.execute(
                "SELECT order_ids FROM bills WHERE client_id=%s AND table_no=%s AND payment_status='paid' AND DATE(created_at::timestamp)=%s",
                (client_id, table_no, today)
            )
            for row in cur6.fetchall():
                paid_today_ids.extend(_json.loads(row["order_ids"]))
        except Exception:
            paid_today_ids = []
        t["paid_today_order_ids"] = paid_today_ids

        result.append(t)

    conn.close()
    return result


# ════════════════════════════════
# ORDER OPERATIONS
# ════════════════════════════════

def place_order(client_id: str, table_no: int, items: list,
                total: int, source: str = "customer",
                customer_name: str = None, customer_phone: str = None):
    import json
    conn = get_db()
    cur = conn._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO orders (client_id, table_no, source, customer_name, customer_phone, items, total)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (client_id, table_no, source, customer_name, customer_phone, json.dumps(items), total))
    order_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()
    return order_id

def get_orders(client_id: str, status: str = None, table_no: int = None, source: str = None, from_date: str = None):
    conn = get_db()
    query = "SELECT * FROM orders WHERE client_id=%s"
    params = [client_id]
    if status:
        query += " AND status=%s"
        params.append(status)
    if table_no:
        query += " AND table_no=%s"
        params.append(table_no)
    if source:
        query += " AND source=%s"
        params.append(source)
    if from_date:
        query += " AND DATE(created_at::timestamp) >= %s"
        params.append(from_date)
    query += " ORDER BY created_at DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_order_status(order_id: int, status: str):
    conn = get_db()
    conn.execute("""
        UPDATE orders SET status=%s, updated_at=TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        WHERE id=%s
    """, (status, order_id))
    conn.commit()
    conn.close()

def update_ready_items(order_id: int, ready_items: list):
    import json
    conn = get_db()
    conn.execute(
        "UPDATE orders SET ready_items=%s, updated_at=TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS') WHERE id=%s",
        (json.dumps(ready_items), order_id)
    )
    conn.commit()
    conn.close()

def get_table_orders_detail(client_id: str, table_no: int):
    """Full orders for current session with billing context"""
    import json as _json

    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM tables WHERE client_id=%s AND table_no=%s",
        (client_id, table_no)
    )
    table = cur.fetchone()

    opened_at = "1970-01-01 00:00:00"
    if table:
        raw = dict(table).get("opened_at") or "1970-01-01 00:00:00"
        opened_at = raw.replace("T", " ").split(".")[0]

    cur2 = conn.execute("""
        SELECT * FROM orders
        WHERE client_id=%s AND table_no=%s AND created_at >= %s
        ORDER BY created_at DESC
    """, (client_id, table_no, opened_at))
    orders = [dict(o) for o in cur2.fetchall()]

    cur3 = conn.execute("""
        SELECT * FROM bills
        WHERE client_id=%s AND table_no=%s AND created_at >= %s
        ORDER BY created_at DESC
    """, (client_id, table_no, opened_at))
    bills = [dict(b) for b in cur3.fetchall()]

    for b in bills:
        b["order_ids"] = _json.loads(b["order_ids"])

    paid_order_ids = set()
    for b in bills:
        if b["payment_status"] == "paid":
            paid_order_ids.update(b["order_ids"])

    for o in orders:
        o["items"] = _json.loads(o["items"])
        o["billed"] = o["id"] in paid_order_ids

    conn.close()
    return {"orders": orders, "bills": bills}


# ════════════════════════════════
# BILL OPERATIONS
# ════════════════════════════════

def generate_bill(client_id: str, table_no: int,
                  customer_name: str = None, customer_phone: str = None,
                  tax_percent: float = 0.0, discount: int = 0,
                  payment_mode: str = None):
    import json
    orders = get_orders(client_id, table_no=table_no)

    conn = get_db()
    cur = conn.execute("""
        SELECT order_ids FROM bills
        WHERE client_id=%s AND table_no=%s AND payment_status='paid'
    """, (client_id, table_no))
    paid_bills = cur.fetchall()
    conn.close()

    already_billed_ids = set()
    for b in paid_bills:
        already_billed_ids.update(json.loads(b["order_ids"]))

    billable = [
        o for o in orders
        if o["status"] == "done" and o["id"] not in already_billed_ids
    ]

    if not billable:
        return None

    order_ids = [o["id"] for o in billable]
    subtotal = sum(o["total"] for o in billable)
    tax = int(subtotal * tax_percent / 100)
    total = subtotal + tax - discount

    conn = get_db()
    cur2 = conn._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur2.execute("""
        INSERT INTO bills (client_id, table_no, order_ids, customer_name, customer_phone,
                           subtotal, tax, discount, total, payment_mode)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (client_id, table_no, json.dumps(order_ids),
          customer_name, customer_phone,
          subtotal, tax, discount, total, payment_mode))
    bill_id = cur2.fetchone()["id"]
    conn.commit()
    conn.close()

    return {
        "bill_id": bill_id,
        "client_id": client_id,
        "table_no": table_no,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "order_ids": order_ids,
        "subtotal": subtotal,
        "tax": tax,
        "discount": discount,
        "total": total,
        "payment_mode": payment_mode,
        "orders": billable
    }

def get_bill(bill_id: int):
    import json
    conn = get_db()
    cur = conn.execute("SELECT * FROM bills WHERE id=%s", (bill_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    bill = dict(row)
    bill["order_ids"] = json.loads(bill["order_ids"])
    return bill

def mark_bill_paid(bill_id: int, payment_mode: str):
    conn = get_db()
    conn.execute("""
        UPDATE bills SET payment_status='paid', payment_mode=%s WHERE id=%s
    """, (payment_mode, bill_id))
    conn.commit()
    conn.close()


# ════════════════════════════════
# ADMIN / ANALYTICS
# ════════════════════════════════

def get_summary(client_id: str):
    conn = get_db()
    total_orders = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s", (client_id,)
    )._conn  # use raw fetch below
    # Rewrite to use raw cursor for scalar queries
    conn2 = get_db()
    raw = conn2._conn.cursor()

    raw.execute("SELECT COUNT(*) FROM orders WHERE client_id=%s", (client_id,))
    total_orders = raw.fetchone()[0]

    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid'",
        (client_id,)
    )
    total_revenue = raw.fetchone()[0]

    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s AND status='pending'",
        (client_id,)
    )
    pending_orders = raw.fetchone()[0]

    raw.execute(
        "SELECT COUNT(*) FROM tables WHERE client_id=%s AND status != 'inactive'",
        (client_id,)
    )
    active_tables = raw.fetchone()[0]

    conn.close()
    conn2.close()
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "active_tables": active_tables
    }

def get_analytics(client_id: str):
    """Rich analytics for owner dashboard."""
    import json as _json
    from datetime import date, timedelta

    conn = get_db()
    raw = conn._conn.cursor()
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s AND DATE(created_at::timestamp)=%s AND status != 'cancelled'",
        (client_id, today)
    )
    today_orders = raw.fetchone()[0]

    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid' AND DATE(created_at::timestamp)=%s",
        (client_id, today)
    )
    today_revenue = raw.fetchone()[0]

    raw.execute(
        "SELECT COUNT(*) FROM bills WHERE client_id=%s AND payment_status='paid' AND DATE(created_at::timestamp)=%s",
        (client_id, today)
    )
    today_bills = raw.fetchone()[0]

    today_avg = round(today_revenue / today_bills, 0) if today_bills > 0 else 0

    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s AND DATE(created_at::timestamp)=%s AND status != 'cancelled'",
        (client_id, yesterday)
    )
    yest_orders = raw.fetchone()[0]

    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid' AND DATE(created_at::timestamp)=%s",
        (client_id, yesterday)
    )
    yest_revenue = raw.fetchone()[0]

    def pct_change(today_val, yest_val):
        if yest_val == 0:
            return None
        return round((today_val - yest_val) / yest_val * 100, 1)

    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s AND status != 'cancelled'", (client_id,)
    )
    alltime_orders = raw.fetchone()[0]

    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid'",
        (client_id,)
    )
    alltime_revenue = raw.fetchone()[0]

    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE client_id=%s AND status='pending'", (client_id,)
    )
    pending_now = raw.fetchone()[0]

    raw.execute(
        "SELECT COUNT(*) FROM tables WHERE client_id=%s AND status != 'inactive'", (client_id,)
    )
    active_tables = raw.fetchone()[0]

    raw.execute(
        "SELECT items FROM orders WHERE client_id=%s AND status != 'cancelled'", (client_id,)
    )
    all_orders_items = raw.fetchall()

    item_counts = {}
    item_revenue = {}
    for row in all_orders_items:
        try:
            items = _json.loads(row[0])
            for it in items:
                name = it.get("name", "")
                qty = it.get("qty", 0)
                price = it.get("price", 0)
                item_counts[name] = item_counts.get(name, 0) + qty
                item_revenue[name] = item_revenue.get(name, 0) + qty * price
        except Exception:
            pass

    top_items = sorted(
        [{"name": k, "qty": v, "revenue": item_revenue.get(k, 0)} for k, v in item_counts.items()],
        key=lambda x: x["qty"], reverse=True
    )[:8]

    raw.execute(
        """SELECT payment_mode, COUNT(*) as cnt, COALESCE(SUM(total),0) as rev
           FROM bills WHERE client_id=%s AND payment_status='paid'
           GROUP BY payment_mode""",
        (client_id,)
    )
    pay_rows = raw.fetchall()
    payment_breakdown = [{"mode": r[0] or "unknown", "count": r[1], "revenue": r[2]} for r in pay_rows]

    raw.execute(
        """SELECT EXTRACT(HOUR FROM created_at::timestamp)::INTEGER as hr, COUNT(*) as cnt
           FROM orders WHERE client_id=%s AND DATE(created_at::timestamp)=%s AND status != 'cancelled'
           GROUP BY hr ORDER BY hr""",
        (client_id, today)
    )
    hourly_rows = raw.fetchall()
    hourly = {r[0]: r[1] for r in hourly_rows}
    hourly_data = [{"hour": h, "orders": hourly.get(h, 0)} for h in range(8, 24)]

    raw.execute(
        """SELECT DATE(created_at::timestamp) as day, COALESCE(SUM(total),0) as rev, COUNT(*) as cnt
           FROM bills WHERE client_id=%s AND payment_status='paid'
           AND DATE(created_at::timestamp) >= CURRENT_DATE - INTERVAL '6 days'
           GROUP BY day ORDER BY day""",
        (client_id,)
    )
    daily_rows = raw.fetchall()
    daily_map = {str(r[0]): {"revenue": r[1], "orders": r[2]} for r in daily_rows}
    daily_data = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        daily_data.append({
            "date": d,
            "label": (date.today() - timedelta(days=i)).strftime("%a"),
            "revenue": daily_map.get(d, {}).get("revenue", 0),
            "orders": daily_map.get(d, {}).get("orders", 0)
        })

    raw.execute(
        """SELECT source, COUNT(*) as cnt FROM orders
           WHERE client_id=%s AND DATE(created_at::timestamp)=%s AND status != 'cancelled'
           GROUP BY source""",
        (client_id, today)
    )
    source_rows = raw.fetchall()
    source_today = {r[0]: r[1] for r in source_rows}

    conn.close()

    return {
        "today": {
            "orders": today_orders,
            "revenue": today_revenue,
            "bills_paid": today_bills,
            "avg_order_value": int(today_avg),
            "orders_change_pct": pct_change(today_orders, yest_orders),
            "revenue_change_pct": pct_change(today_revenue, yest_revenue),
            "source_breakdown": source_today,
        },
        "alltime": {
            "orders": alltime_orders,
            "revenue": alltime_revenue,
            "pending_now": pending_now,
            "active_tables": active_tables,
        },
        "top_items": top_items,
        "payment_breakdown": payment_breakdown,
        "hourly_today": hourly_data,
        "daily_last7": daily_data,
    }


if __name__ == "__main__":
    init_db()


# ════════════════════════════════
# ADMIN PANEL — EXTRA FUNCTIONS
# ════════════════════════════════

def get_all_restaurants_info():
    """Saare restaurants ki basic info + staff count + today orders"""
    import os, json
    from datetime import date
    data_dir = "data"
    restaurants = []
    if not os.path.exists(data_dir):
        return []
    conn = get_db()
    raw = conn._conn.cursor()
    today = date.today().isoformat()
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        client_id = fname.replace(".json", "")
        try:
            with open(f"{data_dir}/{fname}", encoding="utf-8") as f:
                rdata = json.load(f)
            rinfo = rdata.get("restaurant", {})
        except:
            rinfo = {}
        raw.execute(
            "SELECT COUNT(*) FROM staff WHERE restaurant_id=%s", (client_id,)
        )
        staff_count = raw.fetchone()[0]
        raw.execute(
            "SELECT COUNT(*) FROM orders WHERE client_id=%s AND DATE(created_at::timestamp)=%s AND status != 'cancelled'",
            (client_id, today)
        )
        today_orders = raw.fetchone()[0]
        raw.execute(
            "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid' AND DATE(created_at::timestamp)=%s",
            (client_id, today)
        )
        today_revenue = raw.fetchone()[0]
        raw.execute(
            "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=%s AND payment_status='paid'",
            (client_id,)
        )
        alltime_revenue = raw.fetchone()[0]
        restaurants.append({
            "client_id": client_id,
            "name": rinfo.get("name", client_id),
            "cuisine_type": rinfo.get("cuisine_type", ""),
            "phone": rinfo.get("phone", ""),
            "num_tables": rinfo.get("num_tables", 0),
            "staff_count": staff_count,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "alltime_revenue": alltime_revenue,
            "features": rdata.get("subscription", {}).get("features", ["basic"]),
        })
    conn.close()
    return restaurants

def get_overall_stats():
    """Poore platform ki stats"""
    from datetime import date
    conn = get_db()
    raw = conn._conn.cursor()
    today = date.today().isoformat()
    total_restaurants = len([
        f for f in __import__('os').listdir("data")
        if f.endswith(".json")
    ]) if __import__('os').path.exists("data") else 0
    raw.execute("SELECT COUNT(*) FROM staff WHERE is_active=1")
    total_staff = raw.fetchone()[0]
    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE DATE(created_at::timestamp)=%s AND status != 'cancelled'", (today,)
    )
    today_orders = raw.fetchone()[0]
    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE payment_status='paid' AND DATE(created_at::timestamp)=%s", (today,)
    )
    today_revenue = raw.fetchone()[0]
    raw.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE payment_status='paid'"
    )
    alltime_revenue = raw.fetchone()[0]
    raw.execute(
        "SELECT COUNT(*) FROM orders WHERE status != 'cancelled'"
    )
    alltime_orders = raw.fetchone()[0]
    conn.close()
    return {
        "total_restaurants": total_restaurants,
        "total_staff": total_staff,
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "alltime_revenue": alltime_revenue,
        "alltime_orders": alltime_orders,
    }

def get_top_dishes_overall(limit=10, period='alltime'):
    """Saare restaurants ke top dishes — period: alltime | today | week | month"""
    import json as _json
    from datetime import date, timedelta
    conn = get_db()
    raw = conn._conn.cursor()

    today = date.today().isoformat()
    if period == 'today':
        date_filter = f"AND DATE(created_at::timestamp) = '{today}'"
    elif period == 'week':
        week_start = (date.today() - timedelta(days=6)).isoformat()
        date_filter = f"AND DATE(created_at::timestamp) >= '{week_start}'"
    elif period == 'month':
        month_start = (date.today() - timedelta(days=29)).isoformat()
        date_filter = f"AND DATE(created_at::timestamp) >= '{month_start}'"
    else:
        date_filter = ""

    raw.execute(
        f"SELECT items FROM orders WHERE status != 'cancelled' {date_filter}"
    )
    rows = raw.fetchall()
    conn.close()
    item_counts = {}
    item_revenue = {}
    for row in rows:
        try:
            items = _json.loads(row[0])
            for it in items:
                name = it.get("name", "")
                qty = it.get("qty", 0)
                price = it.get("price", 0)
                item_counts[name] = item_counts.get(name, 0) + qty
                item_revenue[name] = item_revenue.get(name, 0) + qty * price
        except:
            pass
    top = sorted(
        [{"name": k, "qty": v, "revenue": item_revenue.get(k, 0)} for k, v in item_counts.items()],
        key=lambda x: x["qty"], reverse=True
    )[:limit]
    return top

def save_restaurant_json(client_id: str, data: dict):
    """Restaurant JSON save karo"""
    import json
    with open(f"data/{client_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def delete_restaurant_full(client_id: str):
    """Poora restaurant delete — DB + JSON"""
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE client_id=%s", (client_id,))
    conn.execute("DELETE FROM bills WHERE client_id=%s", (client_id,))
    conn.execute("DELETE FROM tables WHERE client_id=%s", (client_id,))
    conn.execute("DELETE FROM staff WHERE restaurant_id=%s", (client_id,))
    conn.commit()
    conn.close()
    json_path = f"data/{client_id}.json"
    if __import__('os').path.exists(json_path):
        __import__('os').remove(json_path)
