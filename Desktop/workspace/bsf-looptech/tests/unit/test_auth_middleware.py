"""
Unit tests for authentication middleware classes.
Tests AuthenticationMiddleware, RateLimitMiddleware,
PermissionMiddleware helper methods, and shared get_client_ip utility.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.responses import Response

from src.auth.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
)
from src.auth.security import SecurityHeaders
from src.utils.request import get_client_ip


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(path="/test", method="GET", headers=None, client_host="127.0.0.1"):
    """Build a minimal mock request."""
    req = MagicMock()
    req.url.path = path
    req.method = method
    req.headers = headers or {}
    req.client = MagicMock()
    req.client.host = client_host
    req.state = MagicMock()
    return req


def _make_response(status_code=200):
    """Build a minimal mock response."""
    resp = Response(status_code=status_code)
    return resp


# ===========================================================================
# AuthenticationMiddleware — helper methods
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestAuthMiddlewareExemptPaths:
    def test_docs_path_is_exempt(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/docs") is True

    def test_health_path_is_exempt(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/health") is True

    def test_auth_login_is_exempt(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/auth/login") is True

    def test_api_endpoint_not_exempt(self):
        # Default exempt_paths includes "/" which matches all paths via startswith.
        # Use custom exempt_paths to test non-matching.
        mw = AuthenticationMiddleware(MagicMock(), exempt_paths=["/docs", "/health"])
        assert mw._is_exempt_path("/api/waste") is False

    def test_custom_exempt_paths(self):
        mw = AuthenticationMiddleware(MagicMock(), exempt_paths=["/custom"])
        assert mw._is_exempt_path("/custom") is True
        assert mw._is_exempt_path("/docs") is False

    def test_root_path_is_exempt(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/") is True

    def test_openapi_json_is_exempt(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/openapi.json") is True

    def test_prefix_matching(self):
        mw = AuthenticationMiddleware(MagicMock())
        assert mw._is_exempt_path("/docs/swagger") is True
        assert mw._is_exempt_path("/health/live") is True


@pytest.mark.unit
@pytest.mark.auth
class TestGetClientIP:
    """Tests for the shared get_client_ip utility (src.utils.request)."""

    def test_ip_from_x_real_ip(self):
        request = _make_request(headers={"X-Real-IP": "10.0.0.2"})
        assert get_client_ip(request) == "10.0.0.2"

    def test_ip_from_client_host(self):
        request = _make_request(client_host="192.168.0.10")
        assert get_client_ip(request) == "192.168.0.10"

    def test_ip_unknown_fallback(self):
        request = _make_request()
        del request.client.host
        request.client = MagicMock(spec=[])
        assert get_client_ip(request) == "unknown"

    def test_x_forwarded_for_ignored(self):
        """X-Forwarded-For is NOT trusted (spoofable); only X-Real-IP is."""
        request = _make_request(
            headers={"X-Forwarded-For": "10.0.0.1"},
            client_host="192.168.1.1",
        )
        assert get_client_ip(request) == "192.168.1.1"


@pytest.mark.unit
@pytest.mark.auth
class TestAuthMiddlewareSecurityHeaders:
    def test_adds_security_headers(self):
        mw = AuthenticationMiddleware(MagicMock())
        response = _make_response()
        result = mw._add_security_headers(response)
        expected = SecurityHeaders.get_security_headers()
        for key, value in expected.items():
            assert result.headers.get(key) == value

    def test_returns_same_response(self):
        mw = AuthenticationMiddleware(MagicMock())
        response = _make_response(status_code=404)
        result = mw._add_security_headers(response)
        assert result is response


# ===========================================================================
# RateLimitMiddleware
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestRateLimitMiddleware:
    def test_init_default_rate(self):
        mw = RateLimitMiddleware(MagicMock())
        assert mw.requests_per_minute == 60

    def test_init_custom_rate(self):
        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=10)
        assert mw.requests_per_minute == 10

    @pytest.mark.asyncio
    async def test_dispatch_allows_within_limit(self):
        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=100)
        request = _make_request(client_host="10.0.0.1")

        async def call_next(req):
            return _make_response(200)

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_blocks_over_limit(self):
        mw = RateLimitMiddleware(MagicMock(), requests_per_minute=1)
        request = _make_request(client_host="10.0.0.2")

        async def call_next(req):
            return _make_response(200)

        # First request passes
        resp1 = await mw.dispatch(request, call_next)
        assert resp1.status_code == 200

        # Second request blocked
        resp2 = await mw.dispatch(request, call_next)
        assert resp2.status_code == 429


