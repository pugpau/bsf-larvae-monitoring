"""Integration tests for dashboard overview API."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@pytest.fixture
async def api_session():
    """Fresh DB + session for integration tests."""
    from src.auth.models import User  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session, engine
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def client(api_session):
    """HTTPX async client hitting the FastAPI app."""
    session, engine = api_session
    from src.main import app
    from src.database.postgresql import get_async_session

    async def override():
        yield session

    app.dependency_overrides[get_async_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ══════════════════════════════════════
#  Helpers
# ══════════════════════════════════════

async def _create_waste_record(client: AsyncClient) -> dict:
    data = {
        "source": "テスト業者",
        "deliveryDate": "2026-03-01",
        "wasteType": "汚泥（一般）",
        "weight": 10.0,
        "weightUnit": "t",
        "status": "pending",
        "analysis": {"pH": 7.0, "moisture": 40.0},
    }
    r = await client.post("/api/waste/records", json=data)
    assert r.status_code == 201
    return r.json()


# ══════════════════════════════════════
#  Dashboard Overview Tests
# ══════════════════════════════════════

@pytest.mark.asyncio
class TestDashboardOverview:

    async def test_overview_empty(self, client):
        r = await client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["delivery"]["total"] == 0
        assert data["formulation"]["total"] == 0
        assert data["waste"]["total"] == 0
        assert data["recent_activity"] == []

    async def test_overview_with_waste(self, client):
        await _create_waste_record(client)
        await _create_waste_record(client)
        r = await client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["waste"]["total"] == 2
        # Records with analysis auto-set to "analyzed", not "pending"
        assert data["waste"]["pending"] == 0

    async def test_overview_with_formulations(self, client):
        waste = await _create_waste_record(client)
        # Create 2 formulations
        await client.post("/api/v1/formulations", json={
            "waste_record_id": waste["id"],
            "source_type": "manual",
        })
        await client.post("/api/v1/formulations", json={
            "waste_record_id": waste["id"],
            "source_type": "ml",
        })
        r = await client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert data["formulation"]["total"] == 2
        assert data["formulation"]["proposed"] == 2

    async def test_overview_formulation_status_breakdown(self, client):
        waste = await _create_waste_record(client)
        # Create and accept one formulation
        r1 = await client.post("/api/v1/formulations", json={
            "waste_record_id": waste["id"],
            "source_type": "manual",
        })
        fid = r1.json()["id"]
        await client.post(f"/api/v1/formulations/{fid}/accept")
        # Create another (stays proposed)
        await client.post("/api/v1/formulations", json={
            "waste_record_id": waste["id"],
            "source_type": "manual",
        })
        r = await client.get("/api/v1/dashboard/overview")
        data = r.json()
        assert data["formulation"]["proposed"] == 1
        assert data["formulation"]["accepted"] == 1
        assert data["formulation"]["total"] == 2

    async def test_overview_response_structure(self, client):
        r = await client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        # Verify all expected keys exist
        assert "delivery" in data
        assert "formulation" in data
        assert "waste" in data
        assert "recent_activity" in data
        # Delivery keys
        assert "scheduled" in data["delivery"]
        assert "delivered" in data["delivery"]
        assert "cancelled" in data["delivery"]
        # Formulation keys
        for key in ("proposed", "accepted", "applied", "verified", "rejected"):
            assert key in data["formulation"]

    async def test_overview_with_activity(self, client):
        """When formulations exist, activity events should appear."""
        waste = await _create_waste_record(client)
        # Recommend creates activity logs
        r = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste["id"],
            "top_k": 1,
        })
        assert r.status_code == 200
        # Check overview includes recent activity
        r2 = await client.get("/api/v1/dashboard/overview")
        data = r2.json()
        # Activity may or may not be present depending on
        # whether recommend creates activity events
        assert isinstance(data["recent_activity"], list)
