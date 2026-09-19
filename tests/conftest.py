"""
tests/conftest.py — Pytest fixtures & mocks

Ye file real Neon DB ko touch NAHI karta.
Sab kuch mock hai — sirf API endpoints test ho rahe hain.

Setup:
    pip install pytest pytest-asyncio httpx

Run:
    pytest tests/ -v
    pytest tests/test_smoke.py -v
    pytest tests/test_billing.py -v
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

try:
    from fastapi.testclient import TestClient
except ImportError:
    from starlette.testclient import TestClient

# ── Env vars test ke liye (real values nahi chahiye) ──
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("GLB_SECRET", "test-glb-secret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("DATABASE_URL", "postgresql://fake:fake@fake/fake")
os.environ.setdefault("ZENTABLE_UPI_ID", "test@upi")

# ════════════════════════════════
# CRITICAL — psycopg2 pool ko mock karo
# database.py import hote hi module-level pe pool banana shuru karta hai
# Isliye mock PEHLE lagana padta hai — koi bhi import se pehle
# ════════════════════════════════

_mock_pool = MagicMock()
_mock_pool.getconn.return_value = MagicMock()

_psycopg2_mock = MagicMock()
_psycopg2_mock.pool.ThreadedConnectionPool.return_value = _mock_pool
_psycopg2_mock.extras.RealDictCursor = None
_psycopg2_mock.OperationalError = Exception

sys.modules["psycopg2"]                = _psycopg2_mock
sys.modules["psycopg2.pool"]           = _psycopg2_mock.pool
sys.modules["psycopg2.extras"]         = _psycopg2_mock.extras
sys.modules["psycopg2.extensions"]     = MagicMock()

# ════════════════════════════════
# HEAVY MOCKS — DB aur external calls band karo
# ════════════════════════════════

# Ye sab patches import hone se PEHLE lagane padte hain
# isliye conftest.py mein hain

MOCK_RESTAURANT = {
    "client_id": "test_resto",
    "name": "Test Restaurant",
    "status": "active",
}

MOCK_OWNER_TOKEN_PAYLOAD = {
    "sub":       "test_resto",
    "client_id": "test_resto",
    "branch_id": None,
    "role":      "owner",
    "name":      "Test Owner",
    "owner_id":  1,
}

MOCK_ADMIN_TOKEN_PAYLOAD = {
    "sub":      "admin",
    "role":     "admin",
    "name":     "Super Admin",
    "admin_id": 1,
}

MOCK_SUBSCRIPTION = {
    "client_id":        "test_resto",
    "status":           "active",
    "plan_key":         "pro",
    "period":           "monthly",
    "base_price":       2999,
    "final_price":      2999,
    "discount_percent": 0,
    "discount_flat":    0,
    "starts_at":        "2025-01-01",
    "ends_at":          "2099-12-31",
    "trial_ends_at":    None,
    "admin_notes":      None,
}

MOCK_PLANS = [
    {
        "key": "basic", "name": "Basic", "monthly_price": 1499,
        "features": {"included": ["website", "qr_ordering"], "labels": {}},
    },
    {
        "key": "pro", "name": "Pro", "monthly_price": 2999,
        "features": {"included": ["website", "qr_ordering", "owner_analytics"], "labels": {}},
    },
    {
        "key": "elite", "name": "Elite", "monthly_price": 5499,
        "features": {"included": ["website", "qr_ordering", "owner_analytics", "centralized_reporting"], "labels": {}},
    },
]

MOCK_ADDONS = [
    {"key": "ar_menu", "name": "AR Menu", "monthly_price": 499, "one_time_only": False},
    {"key": "kitchen_tab", "name": "Kitchen Tab", "monthly_price": 299, "one_time_only": True},
]


@pytest.fixture(scope="session")
def mock_patches():
    """
    Session-wide patches — ek baar lagao, sab tests mein kaam kare.
    Real DB, R2, aur external calls sab mock hain.
    """
    patches = [
        # Database
        patch("db.init_all"),
        patch("db.seed_tables"),
        patch("db.get_all_restaurants_info", return_value=[MOCK_RESTAURANT]),
        patch("db.get_all_site_settings", return_value={}),
        patch("db.get_db", return_value=MagicMock()),

        # Billing DB
        patch("db.billing_db.init_billing_tables"),
        patch("db.billing_db.sync_plan_features"),
        patch("db.billing_db.run_daily_billing_cron"),
        patch("db.billing_db.get_all_plans", return_value=MOCK_PLANS),
        patch("db.billing_db.get_all_addons", return_value=MOCK_ADDONS),
        patch("db.billing_db.get_subscription", return_value=MOCK_SUBSCRIPTION),
        patch("db.billing_db.get_all_subscriptions", return_value=[MOCK_SUBSCRIPTION]),
        patch("db.billing_db.get_plan", side_effect=lambda key: next((p for p in MOCK_PLANS if p["key"] == key), None)),
        patch("db.billing_db.get_addon", side_effect=lambda key: next((a for a in MOCK_ADDONS if a["key"] == key), None)),
        patch("db.billing_db.get_subscription_addons", return_value=[]),

        # Blog DB
        patch("db.blog_db.init_blog_tables"),
        patch("db.blog_db.get_published_posts", return_value=[]),

        # Helpers
        patch("helpers.get_client_data", return_value={
            "restaurant": {
                "num_tables": 5,
                "name": "Test",
                "tagline": "Test Tagline",
                "logo": "/static/assets/logo.png",
                "banner": "/static/assets/banner.png",
                "timings": {"lunch": "12-3", "dinner": "7-11", "closed": "Monday"},
                "social": {"instagram": "", "facebook": "", "twitter": ""},
            },
            "theme": {
                "primary_color": "#D4AF37", "secondary_color": "#1a1a1a",
                "accent_color": "#8B4513", "text_color": "#333333",
                "background": "#ffffff", "font_primary": "Playfair Display",
                "font_secondary": "Poppins",
            },
            "items": []
        }),
        patch("helpers.is_restaurant_active", return_value=True),
        patch("helpers.get_restaurant_branches", return_value=[
            {"branch_id": "__default__", "config": {}}
        ], create=True),

        # Trash
        patch("trash_utils.purge_expired_trash"),

        # R2
        patch("r2.USE_R2", False),
        patch("r2.IS_PROD", False),
        patch("r2.r2_public_url", return_value="http://fake-r2/file.glb"),

        # Database branches
        patch("db.get_restaurant_branches", return_value=[
            {"branch_id": "__default__", "config": {}}
        ]),
    ]

    started = [p.start() for p in patches]
    yield started
    for p in patches:
        p.stop()


@pytest.fixture(scope="session")
def client(mock_patches):
    """
    FastAPI TestClient — real server nahi chalana padta.
    mock_patches pehle lagta hai, phir app import hota hai.
    """
    from main import app
    with TestClient(app, raise_server_exceptions=True, follow_redirects=False) as c:
        yield c


def make_token(payload: dict) -> str:
    """Test ke liye valid JWT token banao"""
    from auth import create_token
    return create_token(payload, payload.get("role", "owner"))


@pytest.fixture
def owner_token():
    """Pro plan wale owner ka token"""
    return make_token(MOCK_OWNER_TOKEN_PAYLOAD)


@pytest.fixture
def admin_token():
    """Admin ka token"""
    return make_token(MOCK_ADMIN_TOKEN_PAYLOAD)


@pytest.fixture
def owner_client(client, owner_token):
    """Cookie set kiya hua owner TestClient"""
    client.cookies.set("auth_token", owner_token)
    yield client
    client.cookies.clear()


@pytest.fixture
def admin_client(client, admin_token):
    """Cookie set kiya hua admin TestClient"""
    client.cookies.set("auth_token", admin_token)
    yield client
    client.cookies.clear()
