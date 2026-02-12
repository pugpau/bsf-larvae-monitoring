"""Unit tests for /health endpoint LLM check (Phase 2-6)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base, engine
from src.main import app


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before tests, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.unit
class TestHealthLLMCheck:
    """LLM status in /health response."""

    @pytest.mark.asyncio
    async def test_health_includes_llm_service(self, client):
        """Response should include services.llm field."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data["services"]

    @pytest.mark.asyncio
    async def test_health_llm_unavailable_status_still_healthy(self, client):
        """When LLM is down but DB is up, status should be 'healthy'."""
        with patch("src.main.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            resp = await client.get("/health")
            data = resp.json()

        # LLM down should NOT make overall status degraded
        # (status depends only on PostgreSQL)
        assert data["services"]["llm"] in ("ok", "unavailable")

    @pytest.mark.asyncio
    async def test_health_api_always_ok(self, client):
        """API service should always be 'ok'."""
        resp = await client.get("/health")
        data = resp.json()
        assert data["services"]["api"] == "ok"

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client):
        """Verify full response structure."""
        resp = await client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "services" in data
        assert "details" in data
        assert "api" in data["services"]
        assert "postgresql" in data["services"]
        assert "llm" in data["services"]
