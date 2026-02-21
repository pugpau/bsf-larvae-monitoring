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
        assert "ERC製品管理システム" in response.json()["message"]


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
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

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
class TestWasteSearchAndPagination:
    async def test_search_by_query(self, client):
        # Create test records
        for name in ["東京工場", "大阪工場", "名古屋工場"]:
            await client.post("/api/waste/records", json={
                "source": name, "deliveryDate": "2026-02-01",
                "wasteType": "汚泥（一般）", "weight": 5.0, "weightUnit": "t",
            })
        response = await client.get("/api/waste/records", params={"q": "東京"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        sources = [r["source"] for r in data["items"]]
        assert any("東京" in s for s in sources)

    async def test_pagination(self, client):
        response = await client.get("/api/waste/records", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["items"]) <= 2

    async def test_sort_order(self, client):
        response = await client.get("/api/waste/records", params={
            "sort_by": "source", "sort_order": "asc"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_invalid_sort_column_still_works(self, client):
        response = await client.get("/api/waste/records", params={"sort_by": "DROP TABLE"})
        assert response.status_code == 200


@pytest.mark.integration
class TestWasteCsvEndpoints:
    async def test_csv_export(self, client):
        await client.post("/api/waste/records", json={
            "source": "CSV工場", "deliveryDate": "2026-02-05",
            "wasteType": "焼却灰", "weight": 8.0, "weightUnit": "t",
        })
        response = await client.get("/api/waste/records/export/csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "source" in content
        assert "CSV工場" in content

    async def test_csv_import(self, client):
        csv_content = "source,deliveryDate,wasteType,weight,weightUnit\nインポート工場,2026-02-06,汚泥（一般）,3.0,t\n"
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        response = await client.post("/api/waste/records/import/csv", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] >= 1
        assert isinstance(data["errors"], list)

    async def test_csv_import_missing_fields(self, client):
        csv_content = "source,deliveryDate\nA,2026-01-01\n"
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        response = await client.post("/api/waste/records/import/csv", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["skipped"] >= 1
        assert len(data["errors"]) >= 1


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
