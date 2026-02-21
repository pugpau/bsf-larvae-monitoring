"""Integration tests for formulation workflow API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@pytest.fixture
async def api_session():
    """Fresh DB + session for integration tests."""
    # Ensure auth models (User table) are registered before create_all
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

async def _create_waste_record(client: AsyncClient, with_analysis: bool = True) -> dict:
    """Create a waste record via API."""
    data = {
        "source": "テスト業者",
        "deliveryDate": "2026-03-01",
        "wasteType": "汚泥（一般）",
        "weight": 10.0,
        "weightUnit": "t",
        "status": "pending",
    }
    if with_analysis:
        data["analysis"] = {
            "pH": 7.0,
            "moisture": 40.0,
            "ignitionLoss": 15.0,
            "Pb": 0.005,
            "As": 0.002,
        }
    r = await client.post("/api/waste/records", json=data)
    assert r.status_code == 201
    return r.json()


async def _create_formulation(client: AsyncClient, waste_record_id: str) -> dict:
    """Create a formulation record via API."""
    r = await client.post("/api/v1/formulations", json={
        "waste_record_id": waste_record_id,
        "source_type": "manual",
        "planned_formulation": {
            "solidifierType": "普通ポルトランドセメント",
            "solidifierAmount": 150.0,
            "solidifierUnit": "kg/t",
        },
        "confidence": 0.8,
        "reasoning": ["手動入力"],
    })
    assert r.status_code == 201
    return r.json()


# ══════════════════════════════════════
#  CRUD Tests
# ══════════════════════════════════════

class TestFormulationCRUD:
    @pytest.mark.asyncio
    async def test_create_formulation(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        assert record["status"] == "proposed"
        assert record["source_type"] == "manual"
        assert record["waste_record_id"] == waste["id"]

    @pytest.mark.asyncio
    async def test_get_formulation(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.get(f"/api/v1/formulations/{record['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == record["id"]

    @pytest.mark.asyncio
    async def test_get_formulation_not_found(self, client):
        r = await client.get("/api/v1/formulations/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_list_formulations(self, client):
        waste = await _create_waste_record(client)
        await _create_formulation(client, waste["id"])
        await _create_formulation(client, waste["id"])
        r = await client.get("/api/v1/formulations")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_waste_record(self, client):
        w1 = await _create_waste_record(client)
        w2 = await _create_waste_record(client)
        await _create_formulation(client, w1["id"])
        await _create_formulation(client, w2["id"])
        r = await client.get(f"/api/v1/formulations?waste_record_id={w1['id']}")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_get_by_waste_record(self, client):
        waste = await _create_waste_record(client)
        await _create_formulation(client, waste["id"])
        r = await client.get(f"/api/v1/formulations/by-waste-record/{waste['id']}")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_update_formulation(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.put(f"/api/v1/formulations/{record['id']}", json={
            "notes": "更新テスト",
        })
        assert r.status_code == 200
        assert r.json()["notes"] == "更新テスト"

    @pytest.mark.asyncio
    async def test_delete_proposed(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.delete(f"/api/v1/formulations/{record['id']}")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client):
        r = await client.delete("/api/v1/formulations/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ══════════════════════════════════════
#  Workflow Tests
# ══════════════════════════════════════

class TestFormulationWorkflow:
    @pytest.mark.asyncio
    async def test_accept(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.post(f"/api/v1/formulations/{record['id']}/accept")
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_apply(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        await client.post(f"/api/v1/formulations/{record['id']}/accept")
        r = await client.post(f"/api/v1/formulations/{record['id']}/apply", json={
            "status": "applied",
            "actual_formulation": {"solidifierAmount": 160.0},
            "actual_cost": 2400.0,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "applied"

    @pytest.mark.asyncio
    async def test_verify(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        await client.post(f"/api/v1/formulations/{record['id']}/accept")
        await client.post(f"/api/v1/formulations/{record['id']}/apply")
        r = await client.post(f"/api/v1/formulations/{record['id']}/verify", json={
            "status": "verified",
            "elution_result": {"Pb": 0.002},
            "elution_passed": True,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "verified"
        assert r.json()["elution_passed"] is True

    @pytest.mark.asyncio
    async def test_reject(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.post(f"/api/v1/formulations/{record['id']}/reject", json={
            "status": "rejected",
            "notes": "コスト超過",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_invalid_transition(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        r = await client.post(f"/api/v1/formulations/{record['id']}/verify", json={
            "status": "verified",
            "elution_result": {"Pb": 0.001},
            "elution_passed": True,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_accepted_fails(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        await client.post(f"/api/v1/formulations/{record['id']}/accept")
        r = await client.delete(f"/api/v1/formulations/{record['id']}")
        assert r.status_code == 400


# ══════════════════════════════════════
#  Recommend Tests
# ══════════════════════════════════════

class TestRecommend:
    @pytest.mark.asyncio
    async def test_recommend_creates_candidates(self, client):
        waste = await _create_waste_record(client)
        r = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste["id"],
            "top_k": 3,
        })
        assert r.status_code == 200
        data = r.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 1
        assert data["waste_record_id"] == waste["id"]

    @pytest.mark.asyncio
    async def test_recommend_no_analysis_fails(self, client):
        waste = await _create_waste_record(client, with_analysis=False)
        r2 = await client.post("/api/v1/formulations/recommend", json={
            "waste_record_id": waste["id"],
        })
        assert r2.status_code == 400


# ══════════════════════════════════════
#  CSV Export Tests
# ══════════════════════════════════════

class TestFormulationCSVExport:
    @pytest.mark.asyncio
    async def test_export_empty(self, client):
        r = await client.get("/api/v1/formulations/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        # BOM + header row only
        text = r.text
        assert text.startswith("\ufeff")
        lines = text.strip().split("\n")
        assert len(lines) == 1  # header only

    @pytest.mark.asyncio
    async def test_export_with_data(self, client):
        waste = await _create_waste_record(client)
        await _create_formulation(client, waste["id"])
        await _create_formulation(client, waste["id"])
        r = await client.get("/api/v1/formulations/export/csv")
        assert r.status_code == 200
        text = r.text.lstrip("\ufeff")
        lines = text.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows
        # Verify header columns
        header = lines[0]
        assert "waste_type" in header
        assert "status" in header
        assert "confidence" in header

    @pytest.mark.asyncio
    async def test_export_filter_by_status(self, client):
        waste = await _create_waste_record(client)
        record = await _create_formulation(client, waste["id"])
        await _create_formulation(client, waste["id"])
        # Accept one record
        await client.post(f"/api/v1/formulations/{record['id']}/accept")
        # Export only accepted
        r = await client.get("/api/v1/formulations/export/csv?status=accepted")
        assert r.status_code == 200
        text = r.text.lstrip("\ufeff")
        lines = text.strip().split("\n")
        assert len(lines) == 2  # header + 1 accepted

    @pytest.mark.asyncio
    async def test_export_filter_by_source_type(self, client):
        waste = await _create_waste_record(client)
        await _create_formulation(client, waste["id"])  # manual
        r = await client.get("/api/v1/formulations/export/csv?source_type=ml")
        assert r.status_code == 200
        text = r.text.lstrip("\ufeff")
        lines = text.strip().split("\n")
        assert len(lines) == 1  # header only (no ml records)

    @pytest.mark.asyncio
    async def test_export_content_disposition(self, client):
        r = await client.get("/api/v1/formulations/export/csv")
        assert r.status_code == 200
        assert 'filename="formulations.csv"' in r.headers.get("content-disposition", "")
