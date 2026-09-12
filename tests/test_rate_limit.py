"""
tests/test_rate_limit.py — Rate Limiting Tests & Regressions

Verifies:
1. rate_limit_key correctly differentiates unauthenticated (IP) vs staff vs admin
2. SlowAPI does not crash with 500 when endpoints return dictionaries (headers_enabled=False check)
3. Hitting rate limit returns 429 with custom JSON error format
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request
from rate_limit import rate_limit_key, limiter
from auth import create_token


class TestRateLimitKey:
    """Test rate_limit_key generation logic"""

    def test_ip_fallback_when_no_token(self):
        """Unauthenticated request should key by IP address"""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {}
        mock_request.client.host = "192.168.1.50"
        key = rate_limit_key(mock_request)
        assert key == "ip:192.168.1.50"

    def test_staff_key_with_valid_token(self):
        """Staff/Owner token should key by staff/restaurant identity"""
        payload = {
            "sub": "waiter1",
            "role": "waiter",
            "restaurant_id": "resto_abc",
            "staff_id": "staff_99",
        }
        token = create_token(payload, role="waiter")
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"auth_token": token}
        key = rate_limit_key(mock_request)
        assert key == "staff:resto_abc:staff_99"

    def test_admin_key_with_admin_token(self):
        """Admin token should key by admin identity"""
        payload = {
            "sub": "superadmin",
            "role": "admin",
            "admin_id": 42,
        }
        token = create_token(payload, role="admin")
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"auth_token": token}
        key = rate_limit_key(mock_request)
        assert key == "admin:42"

    def test_invalid_token_falls_back_to_ip(self):
        """Invalid JWT token should fall back to IP key"""
        mock_request = MagicMock(spec=Request)
        mock_request.cookies = {"auth_token": "invalid.jwt.token"}
        mock_request.client.host = "10.0.0.1"
        key = rate_limit_key(mock_request)
        assert key == "ip:10.0.0.1"


class TestLimiterConfiguration:
    """Verify limiter configuration settings"""

    def test_headers_disabled_to_prevent_500_on_dict_returns(self):
        """headers_enabled must be False so endpoints returning plain dicts don't crash"""
        assert limiter._headers_enabled is False

    def test_swallow_errors_enabled(self):
        """swallow_errors must be True so limiter backend failures don't 500 the app"""
        assert limiter._swallow_errors is True


class TestRateLimitEnforcement:
    """Test actual rate limiting behavior via TestClient"""

    def test_limiter_allows_requests_and_returns_200(self, client):
        """Endpoints returning dicts should return 200 without slowapi Response crashes"""
        with patch("routers.tables.get_client_data", return_value={"restaurant": {}}), \
             patch("routers.tables.create_waiter_call"):
            r = client.post("/api/table/test_resto/1/call")
            assert r.status_code == 200
            assert r.json() == {"message": "Waiter called for table 1"}

    def test_exceeding_rate_limit_returns_429(self, client):
        """Sending requests beyond route limit (3/min) triggers 429 Too Many Requests"""
        with patch("routers.tables.get_client_data", return_value={"restaurant": {}}), \
             patch("routers.tables.create_waiter_call"):
            
            # Send requests up to limit
            status_codes = []
            for _ in range(5):
                r = client.post("/api/table/test_resto/2/call")
                status_codes.append(r.status_code)
            
            # At least one request should be 429
            assert 429 in status_codes
            # Last request must be 429
            last_res = client.post("/api/table/test_resto/2/call")
            assert last_res.status_code == 429
            data = last_res.json()
            assert data.get("error") == "rate_limit_exceeded"
            assert "Too many requests" in data.get("detail", "")
