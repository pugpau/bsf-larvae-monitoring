"""Integration tests for KPI API endpoints (Phase 5-2)."""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import MLPrediction, WasteRecord
from src.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    from src.database.postgresql import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def seed_kpi_data():
    """Insert sample data for KPI tests."""
    from src.database.postgresql import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        for i in range(5):
            session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=now - timedelta(hours=12),
                waste_type="汚泥",
                status="formulated" if i < 3 else "pending",
                elution_result={"Pb": 0.05} if i == 4 else None,
            ))
        for i in range(2):
            session.add(MLPrediction(
                id=uuid.uuid4(),
                method="ml",
                input_features={},
                prediction={},
                confidence=0.85,
                created_at=now - timedelta(hours=6),
            ))
        await session.commit()


class TestKPIRealtime:
    @pytest.mark.asyncio
    async def test_response_format(self, client):
        """Should return valid KPI response structure."""
        resp = await client.get("/api/v1/kpi/realtime")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 7
        assert "processing_volume" in data
        assert "label" in data["processing_volume"]
        assert "value" in data["processing_volume"]
        assert "unit" in data["processing_volume"]
        assert "status" in data["processing_volume"]
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_with_data(self, client, seed_kpi_data):
        """Should compute KPIs from seeded data."""
        resp = await client.get("/api/v1/kpi/realtime?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["processing_volume"]["value"] >= 5
        assert data["formulation_success_rate"]["value"] >= 50.0
        assert data["ml_usage_rate"]["value"] > 0

    @pytest.mark.asyncio
    async def test_invalid_days(self, client):
        """Should return 422 for out-of-range days."""
        resp = await client.get("/api/v1/kpi/realtime?days=0")
        assert resp.status_code == 422

        resp = await client.get("/api/v1/kpi/realtime?days=100")
        assert resp.status_code == 422


class TestKPITrends:
    @pytest.mark.asyncio
    async def test_empty(self, client):
        """Should return trend data with zero values."""
        resp = await client.get("/api/v1/kpi/trends?months=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["months"] == 3
        assert len(data["data"]) == 3

    @pytest.mark.asyncio
    async def test_with_data(self, client, seed_kpi_data):
        """Should include seeded data in current month."""
        resp = await client.get("/api/v1/kpi/trends?months=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_invalid_months(self, client):
        """Should return 422 for out-of-range months."""
        resp = await client.get("/api/v1/kpi/trends?months=0")
        assert resp.status_code == 422

        resp = await client.get("/api/v1/kpi/trends?months=25")
        assert resp.status_code == 422


class TestKPIAlerts:
    @pytest.mark.asyncio
    async def test_response_format(self, client):
        """Should return valid alert response structure."""
        resp = await client.get("/api/v1/kpi/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    @pytest.mark.asyncio
    async def test_with_violations(self, client, seed_kpi_data):
        """Should detect elution violations from seeded data."""
        resp = await client.get("/api/v1/kpi/alerts?days=7")
        assert resp.status_code == 200
        data = resp.json()
        # seed_kpi_data has 1 record with Pb=0.05 (exceeds 0.01 threshold)
        assert data["total"] >= 1
        pb_alerts = [a for a in data["alerts"] if a["metric"] == "Pb"]
        assert len(pb_alerts) >= 1
        assert pb_alerts[0]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_invalid_days(self, client):
        """Should return 422 for out-of-range days."""
        resp = await client.get("/api/v1/kpi/alerts?days=100")
        assert resp.status_code == 422
