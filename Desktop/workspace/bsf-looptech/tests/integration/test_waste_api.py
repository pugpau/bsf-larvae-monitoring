"""
Integration tests for waste treatment API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.database.postgresql import Base, engine
from src.main import app


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before integration tests, drop after."""
    from src.auth.models import User, UserSession, LoginAttempt, APIKey

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.integration
class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data

    async def test_root_returns_message(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert "BSF-LoopTech" in response.json()["message"]


@pytest.mark.integration
class TestWasteRecordEndpoints:
    async def test_create_waste_record(self, client):
        payload = {
            "source": "テスト工場",
            "deliveryDate": "2026-02-01",
            "wasteType": "汚泥（一般）",
            "weight": 10.0,
            "weightUnit": "t",
            "status": "pending",
        }
        response = await client.post("/api/waste/records", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["source"] == "テスト工場"
        assert "id" in data

    async def test_get_waste_records(self, client):
        response = await client.get("/api/waste/records")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_recommend_requires_analysis(self, client):
        payload = {"analysis": {}, "wasteType": "汚泥（一般）"}
        response = await client.post("/api/waste/recommend", json=payload)
        assert response.status_code == 400

    async def test_recommend_with_valid_analysis(self, client, sample_waste_analysis):
        payload = {"analysis": sample_waste_analysis, "wasteType": "汚泥（一般）"}
        response = await client.post("/api/waste/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data
        assert "method" in data
        assert data["method"] in ("similarity", "rule")


@pytest.mark.integration
class TestMaterialTypeEndpoints:
    async def test_create_material_type(self, client):
        payload = {
            "name": "テスト固化剤",
            "category": "solidifier",
            "description": "テスト用",
        }
        response = await client.post("/api/waste/materials", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "テスト固化剤"

    async def test_get_material_types(self, client):
        response = await client.get("/api/waste/materials")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_filter_by_category(self, client):
        response = await client.get("/api/waste/materials", params={"category": "solidifier"})
        assert response.status_code == 200
