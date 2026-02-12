"""Integration tests for Batch API endpoints (Phase 5)."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import BatchJobRun, WasteRecord
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
async def seed_job_runs():
    """Insert sample batch job runs."""
    from src.database.postgresql import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        for i in range(3):
            run = BatchJobRun(
                id=uuid.uuid4(),
                job_name="daily_aggregation",
                status="success" if i < 2 else "failed",
                started_at=datetime.utcnow() - timedelta(days=i),
                completed_at=datetime.utcnow() - timedelta(days=i, hours=-1),
                result_summary={"total_records": 10 + i},
                error_message="test error" if i == 2 else None,
            )
            session.add(run)
        await session.commit()


class TestBatchJobList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        """Should return empty list when no jobs exist."""
        resp = await client.get("/api/v1/batch/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["jobs"] == []

    @pytest.mark.asyncio
    async def test_list_with_data(self, client, seed_job_runs):
        """Should return all job runs."""
        resp = await client.get("/api/v1/batch/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_list_filter_by_name(self, client, seed_job_runs):
        """Should filter by job_name."""
        resp = await client.get("/api/v1/batch/jobs?job_name=weekly_ml_retrain")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        resp = await client.get("/api/v1/batch/jobs?job_name=daily_aggregation")
        assert resp.status_code == 200
        # seed_job_runs may accumulate in shared in-memory DB
        assert resp.json()["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_pagination(self, client, seed_job_runs):
        """Should support limit and offset."""
        resp = await client.get("/api/v1/batch/jobs?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 2
        assert data["total"] >= 3


class TestBatchJobDetail:
    @pytest.mark.asyncio
    async def test_get_existing(self, client, seed_job_runs):
        """Should return job run details."""
        # First get list to find an ID
        list_resp = await client.get("/api/v1/batch/jobs?limit=1")
        job_id = list_resp.json()["jobs"][0]["id"]

        resp = await client.get(f"/api/v1/batch/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["job_name"] == "daily_aggregation"

    @pytest.mark.asyncio
    async def test_get_not_found(self, client):
        """Should return 404 for unknown job ID."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/batch/jobs/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_invalid_id(self, client):
        """Should return 400 for invalid UUID format."""
        resp = await client.get("/api/v1/batch/jobs/not-a-uuid")
        assert resp.status_code == 400


class TestBatchTrigger:
    @pytest.mark.asyncio
    async def test_trigger_daily(self, client):
        """Should successfully trigger daily_aggregation."""
        # Insert a waste record so the job has data
        from src.database.postgresql import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            record = WasteRecord(
                id=uuid.uuid4(),
                source="テスト工場",
                delivery_date=datetime.utcnow() - timedelta(hours=6),
                waste_type="汚泥",
                status="pending",
            )
            session.add(record)
            await session.commit()

        resp = await client.post("/api/v1/batch/trigger/daily_aggregation")
        assert resp.status_code == 200
        data = resp.json()
        assert "completed successfully" in data["message"]
        assert data["job_run_id"] != "unknown"

    @pytest.mark.asyncio
    async def test_trigger_invalid_job(self, client):
        """Should return 404 for unknown job name."""
        resp = await client.post("/api/v1/batch/trigger/nonexistent_job")
        assert resp.status_code == 404
        assert "Unknown job" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_trigger_monthly(self, client):
        """Should successfully trigger monthly_report."""
        resp = await client.post("/api/v1/batch/trigger/monthly_report")
        assert resp.status_code == 200


class TestSchedulerStatus:
    @pytest.mark.asyncio
    async def test_status(self, client):
        """Should return scheduler status."""
        resp = await client.get("/api/v1/batch/status")
        assert resp.status_code == 200
        data = resp.json()
        # In test env, BATCH_ENABLED=false so scheduler is not running
        assert "running" in data
        assert "jobs" in data
