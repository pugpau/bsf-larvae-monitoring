"""
Tests for /ready and /health endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── /health endpoint ──
# /health does `from src.database.postgresql import check_database_health` locally,
# so we patch at the module where the function lives.

_HEALTH_PATCH = "src.database.postgresql.check_database_health"


async def test_health_returns_200_when_db_healthy(client):
    with patch(_HEALTH_PATCH, new_callable=AsyncMock, return_value=True):
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["services"]["api"] == "ok"
    assert body["services"]["postgresql"] == "ok"


async def test_health_returns_degraded_when_db_down(client):
    with patch(_HEALTH_PATCH, new_callable=AsyncMock, return_value=False):
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["services"]["postgresql"] == "error"


async def test_health_returns_degraded_on_exception(client):
    with patch(
        _HEALTH_PATCH,
        new_callable=AsyncMock,
        side_effect=Exception("connection refused"),
    ):
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert "connection refused" in body["details"]["postgresql"]


# ── /ready endpoint ──


async def test_ready_returns_200_when_db_healthy(client):
    with patch(_HEALTH_PATCH, new_callable=AsyncMock, return_value=True):
        resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True


async def test_ready_returns_503_when_db_down(client):
    with patch(_HEALTH_PATCH, new_callable=AsyncMock, return_value=False):
        resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False
    assert "database" in body["reason"]


async def test_ready_returns_503_on_exception(client):
    with patch(
        _HEALTH_PATCH,
        new_callable=AsyncMock,
        side_effect=Exception("timeout"),
    ):
        resp = await client.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False
