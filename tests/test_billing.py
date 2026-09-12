"""
tests/test_billing.py — Billing aur Feature Locking Tests

Ye specifically verify karta hai:
1. has_feature() sahi kaam kar raha hai
2. Plans ke hisaab se features milte hain
3. Expired subscription pe kuch nahi milta
4. Addon features alag se check hote hain

Run: pytest tests/test_billing.py -v
"""

import pytest
from unittest.mock import patch, MagicMock


# ════════════════════════════════
# has_feature() Unit Tests
# ════════════════════════════════

class TestHasFeature:
    """
    billing_db.has_feature() directly test karo — no HTTP needed.
    Ye sabse important tests hain.
    """

    def _has(self, sub, addons, feature_key):
        """Helper — mock SQL result + clear cache ke saath has_feature call karo"""
        from db.billing_db import has_feature, _feature_cache
        _feature_cache.clear()

        if sub is None:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            mock_get_db = MagicMock()
            mock_get_db.__enter__.return_value = mock_conn
            mock_get_db.__exit__.return_value = None
            with patch("db.billing_db.get_db", return_value=mock_get_db):
                return has_feature("test_resto", feature_key)

        row = {
            "status": sub.get("status"),
            "plan_key": sub.get("plan_key"),
            "plan_features": sub.get("features", {"included": [], "labels": {}}),
            "addon_keys": [a["addon_key"] for a in addons if a.get("is_active", True)],
        }
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = row
        mock_get_db = MagicMock()
        mock_get_db.__enter__.return_value = mock_conn
        mock_get_db.__exit__.return_value = None
        with patch("db.billing_db.get_db", return_value=mock_get_db):
            return has_feature("test_resto", feature_key)

    def test_trial_gets_all_features(self):
        """Trial subscription — sab features milne chahiye"""
        sub = {
            "status": "trial",
            "plan_key": "basic",
            "ends_at": "2099-12-31",
        }
        assert self._has(sub, [], "owner_analytics") is True
        assert self._has(sub, [], "ar_menu") is True
        assert self._has(sub, [], "centralized_reporting") is True

    def test_demo_gets_all_features(self):
        """Demo subscription — sab features milne chahiye"""
        sub = {
            "status": "demo",
            "plan_key": "basic",
            "ends_at": "2099-12-31",
        }
        assert self._has(sub, [], "owner_analytics") is True

    def test_expired_gets_nothing(self):
        """Expired subscription — koi feature nahi milna chahiye"""
        sub = {
            "status": "expired",
            "plan_key": "pro",
            "ends_at": "2020-01-01",
        }
        assert self._has(sub, [], "website") is False
        assert self._has(sub, [], "owner_analytics") is False
        assert self._has(sub, [], "qr_ordering") is False

    def test_no_subscription_gets_nothing(self):
        """Subscription hi nahi — kuch nahi milna chahiye"""
        assert self._has(None, [], "website") is False

    def test_basic_plan_features(self):
        """Basic plan — sirf basic features milne chahiye"""
        sub = {
            "status": "active",
            "plan_key": "basic",
            "ends_at": "2099-12-31",
            "features": {
                "included": ["website", "qr_ordering", "digital_menu", "staff_panel",
                             "basic_pos", "ai_menu_import", "blog"],
                "labels": {}
            }
        }
        # Basic mein milna chahiye
        assert self._has(sub, [], "website") is True
        assert self._has(sub, [], "qr_ordering") is True
        assert self._has(sub, [], "blog") is True

        # Basic mein NAHI milna chahiye
        assert self._has(sub, [], "owner_analytics") is False
        assert self._has(sub, [], "ai_chatbot") is False
        assert self._has(sub, [], "centralized_reporting") is False

    def test_pro_plan_features(self):
        """Pro plan — pro + basic features milne chahiye"""
        sub = {
            "status": "active",
            "plan_key": "pro",
            "ends_at": "2099-12-31",
            "features": {
                "included": ["website", "qr_ordering", "owner_analytics",
                             "ai_chatbot", "multi_branch"],
                "labels": {}
            }
        }
        assert self._has(sub, [], "owner_analytics") is True
        assert self._has(sub, [], "ai_chatbot") is True
        assert self._has(sub, [], "multi_branch") is True

        # Elite-only nahi milni chahiye
        assert self._has(sub, [], "centralized_reporting") is False

    def test_elite_plan_features(self):
        """Elite plan — sab plan features milne chahiye"""
        sub = {
            "status": "active",
            "plan_key": "elite",
            "ends_at": "2099-12-31",
            "features": {
                "included": ["website", "qr_ordering", "owner_analytics",
                             "centralized_reporting", "custom_integrations"],
                "labels": {}
            }
        }
        assert self._has(sub, [], "centralized_reporting") is True
        assert self._has(sub, [], "custom_integrations") is True

    def test_addon_feature_with_active_addon(self):
        """Active addon ke saath ar_menu milna chahiye"""
        sub = {
            "status": "active",
            "plan_key": "basic",
            "ends_at": "2099-12-31",
            "features": {"included": ["website"], "labels": {}},
        }
        addons = [{"addon_key": "ar_menu", "ends_at": "2099-12-31", "is_active": True}]
        assert self._has(sub, addons, "ar_menu") is True

    def test_addon_feature_without_addon(self):
        """Addon nahi kharida — ar_menu nahi milna chahiye"""
        sub = {
            "status": "active",
            "plan_key": "elite",  # Elite bhi ho toh bhi addon alag hai
            "ends_at": "2099-12-31",
            "features": {"included": ["website", "owner_analytics"], "labels": {}},
        }
        assert self._has(sub, [], "ar_menu") is False

    def test_addon_expired(self):
        """Expired addon — feature nahi milna chahiye"""
        sub = {
            "status": "active",
            "plan_key": "pro",
            "ends_at": "2099-12-31",
            "features": {"included": ["website"], "labels": {}},
        }
        addons = [{"addon_key": "ar_menu", "ends_at": "2020-01-01", "is_active": False}]  # expired
        assert self._has(sub, addons, "ar_menu") is False


# ════════════════════════════════
# Feature Lock API Tests
# ════════════════════════════════

class TestFeatureLockAPI:
    """
    HTTP level pe feature locking verify karo.
    Pro plan restaurant — basic-only features pe 403 nahi aana chahiye,
    elite-only pe 403 aana chahiye.
    """

    PRO_SUB = {
        "status": "active",
        "plan_key": "pro",
        "ends_at": "2099-12-31",
        "features": {
            "included": ["website", "qr_ordering", "owner_analytics", "ai_chatbot"],
            "labels": {}
        }
    }

    BASIC_SUB = {
        "status": "active",
        "plan_key": "basic",
        "ends_at": "2099-12-31",
        "features": {
            "included": ["website", "qr_ordering"],
            "labels": {}
        }
    }

    def test_features_me_shows_correct_access(self, owner_client):
        """/features/me — pro plan pe owner_analytics True hona chahiye"""
        from db.billing_db import _feature_cache
        _feature_cache["test_resto"] = {
            "data": {
                "status": "active",
                "features": {"website", "qr_ordering", "owner_analytics", "ai_chatbot"}
            },
            "expires": 9999999999.0
        }
        try:
            r = owner_client.get("/api/billing/features/me")
            assert r.status_code == 200
            data = r.json()
            features = data["features"]
            assert features.get("owner_analytics") is True
            assert features.get("ar_menu") is False
        finally:
            _feature_cache.clear()

    def test_features_me_basic_plan_restricted(self, owner_client):
        """/features/me — basic plan pe owner_analytics False hona chahiye"""
        from db.billing_db import _feature_cache
        _feature_cache["test_resto"] = {
            "data": {
                "status": "active",
                "features": {"website", "qr_ordering"}
            },
            "expires": 9999999999.0
        }
        try:
            r = owner_client.get("/api/billing/features/me")
            assert r.status_code == 200
            data = r.json()
            assert data["features"].get("owner_analytics") is False
        finally:
            _feature_cache.clear()

    def test_expired_sub_features_all_false(self, owner_client):
        """/features/me — expired subscription pe sab False"""
        from db.billing_db import _feature_cache
        _feature_cache["test_resto"] = {
            "data": {
                "status": "expired",
                "features": {"website", "qr_ordering", "owner_analytics"}
            },
            "expires": 9999999999.0
        }
        try:
            r = owner_client.get("/api/billing/features/me")
            assert r.status_code == 200
            features = r.json()["features"]
            # Expired mein koi bhi True nahi hona chahiye
            assert all(v is False for v in features.values()), \
                f"Expired sub mein ye features True hain: {[k for k,v in features.items() if v]}"
        finally:
            _feature_cache.clear()


# ════════════════════════════════
# Billing Admin API Tests
# ════════════════════════════════

class TestBillingAdminAPI:

    def test_create_subscription(self, admin_client):
        with patch("db.billing_db.create_subscription", return_value={
            "client_id": "new_resto", "status": "trial", "plan_key": "basic"
        }):
            r = admin_client.post("/api/billing/subscriptions/new_resto", json={
                "status": "trial",
                "plan_key": "basic",
            })
            assert r.status_code == 200

    def test_update_subscription(self, admin_client):
        mock_sub = {
            "client_id": "test_resto", "status": "active",
            "plan_key": "pro", "period": "monthly",
            "discount_percent": 0, "discount_flat": 0,
            "base_price": 2999, "final_price": 2999,
            "trial_ends_at": None, "current_period_ends_at": "2099-12-31",
            "grace_ends_at": None, "admin_notes": None, "payment_method": "manual",
        }
        mock_plan = {"monthly_price": 2999, "features": {"included": [], "labels": {}}}
        with patch("db.billing_db.get_subscription", return_value=mock_sub), \
             patch("db.billing_db.get_plan", return_value=mock_plan), \
             patch("db.billing_db.update_subscription", return_value=mock_sub):
            r = admin_client.patch("/api/billing/subscriptions/test_resto", json={
                "plan_key": "pro"
            })
            assert r.status_code == 200

    def test_confirm_payment(self, admin_client):
        mock_sub = {
            "client_id": "test_resto", "status": "active",
            "plan_key": "pro", "period": "monthly",
            "discount_percent": 0, "discount_flat": 0,
            "base_price": 2999, "final_price": 2999,
            "trial_ends_at": None, "current_period_ends_at": "2099-12-31",
            "grace_ends_at": None, "admin_notes": None, "payment_method": "manual",
        }
        with patch("db.billing_db.get_subscription", return_value=mock_sub), \
             patch("db.billing_db.confirm_payment", return_value={"ok": True}), \
             patch("db.billing_db.generate_reference_id", return_value="ZT-TEST-JAN26"):
            r = admin_client.post("/api/billing/subscriptions/test_resto/confirm-payment", json={
                "amount": 2999,
                "period": "monthly",
                "payment_mode": "upi",
            })
            assert r.status_code == 200

    def test_price_preview_monthly(self, admin_client):
        mock_plan = {"monthly_price": 2999, "features": {"included": [], "labels": {}}}
        with patch("routers.billing.get_plan", return_value=mock_plan):
            r = admin_client.get("/api/billing/preview-price", params={
                "plan_key": "pro",
                "period":   "monthly",
            })
            assert r.status_code == 200
            data = r.json()
            assert "grand_total" in data
            assert "plan" in data
            assert data["period"] == "monthly"

    def test_price_preview_yearly(self, admin_client):
        mock_plan = {"monthly_price": 5499, "features": {"included": [], "labels": {}}}
        with patch("routers.billing.get_plan", return_value=mock_plan):
            r = admin_client.get("/api/billing/preview-price", params={
                "plan_key": "elite",
                "period":   "yearly",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["multiplier"] == 12

    def test_add_addon_to_subscription(self, admin_client):
        with patch("db.billing_db.upsert_subscription_addon", return_value={
            "base_price": 499, "final_price": 499
        }):
            r = admin_client.post("/api/billing/subscriptions/test_resto/addons", json={
                "addon_key": "ar_menu",
                "period":    "monthly",
            })
            assert r.status_code == 200

    def test_remove_addon(self, admin_client):
        with patch("db.billing_db.remove_subscription_addon"):
            r = admin_client.delete("/api/billing/subscriptions/test_resto/addons/ar_menu")
            assert r.status_code == 200

    def test_invalid_plan_key_rejected(self, admin_client):
        """Galat plan key pe 400/404 aana chahiye"""
        r = admin_client.get("/api/billing/preview-price", params={
            "plan_key": "super_ultra_mega",
            "period":   "monthly",
        })
        assert r.status_code in (400, 404, 422)

    def test_non_admin_cannot_access_billing(self, owner_client):
        """Owner billing admin APIs access nahi kar sakta"""
        r = owner_client.get("/api/billing/subscriptions")
        assert r.status_code == 403
