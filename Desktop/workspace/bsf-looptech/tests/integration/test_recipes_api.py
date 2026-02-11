"""Integration tests for Phase 1 recipes API (recipes + recipe_details)."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from src.database.postgresql import Base, engine
from src.main import app


@pytest.fixture(scope="module", autouse=True)
async def init_test_db():
    """Create all tables before integration tests, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def sample_material_id(client):
    """Create a solidification material and return its id for use in recipe details."""
    resp = await client.post("/api/v1/solidification-materials", json={
        "name": f"テスト固化材_{uuid.uuid4().hex[:8]}",
        "material_type": "cement",
    })
    return resp.json()["id"]


# ══════════════════════════════════════
#  Recipes
# ══════════════════════════════════════

class TestRecipeEndpoints:

    @pytest.mark.asyncio
    async def test_create_recipe_without_details(self, client):
        resp = await client.post("/api/v1/recipes", json={
            "name": "基本配合A",
            "waste_type": "汚泥（一般）",
            "target_strength": 500.0,
            "status": "draft",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "基本配合A"
        assert data["waste_type"] == "汚泥（一般）"
        assert data["status"] == "draft"
        assert data["details"] == []

    @pytest.mark.asyncio
    async def test_create_recipe_with_details(self, client, sample_material_id):
        resp = await client.post("/api/v1/recipes", json={
            "name": "詳細付き配合B",
            "waste_type": "焼却灰",
            "details": [
                {
                    "material_id": sample_material_id,
                    "material_type": "solidification",
                    "addition_rate": 150.0,
                    "order_index": 0,
                },
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["details"]) == 1
        assert data["details"][0]["material_type"] == "solidification"
        assert data["details"][0]["addition_rate"] == 150.0

    @pytest.mark.asyncio
    async def test_list_recipes(self, client):
        await client.post("/api/v1/recipes", json={
            "name": "一覧テスト用",
            "waste_type": "汚泥（一般）",
        })
        resp = await client.get("/api/v1/recipes")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    @pytest.mark.asyncio
    async def test_filter_recipes_by_status(self, client):
        await client.post("/api/v1/recipes", json={
            "name": "アクティブ配合",
            "waste_type": "汚泥（一般）",
            "status": "active",
        })
        resp = await client.get("/api/v1/recipes?status=active")
        assert resp.status_code == 200
        body = resp.json()
        for recipe in body["items"]:
            assert recipe["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_recipe_by_id(self, client):
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "取得テスト",
            "waste_type": "焼却灰",
        })
        rid = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/recipes/{rid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "取得テスト"

    @pytest.mark.asyncio
    async def test_update_recipe(self, client):
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "更新前",
            "waste_type": "汚泥（一般）",
            "status": "draft",
        })
        rid = create_resp.json()["id"]
        resp = await client.put(f"/api/v1/recipes/{rid}", json={
            "name": "更新後",
            "status": "active",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "更新後"
        assert resp.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_delete_recipe(self, client):
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "削除対象",
            "waste_type": "焼却灰",
        })
        rid = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/recipes/{rid}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/api/v1/recipes/{rid}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_recipe_not_found(self, client):
        resp = await client.get("/api/v1/recipes/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ══════════════════════════════════════
#  Recipe Details (add/remove)
# ══════════════════════════════════════

class TestRecipeDetailEndpoints:

    @pytest.mark.asyncio
    async def test_add_detail_to_recipe(self, client, sample_material_id):
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "明細追加テスト",
            "waste_type": "汚泥（一般）",
        })
        rid = create_resp.json()["id"]
        resp = await client.post(f"/api/v1/recipes/{rid}/details", json={
            "material_id": sample_material_id,
            "material_type": "solidification",
            "addition_rate": 120.0,
            "order_index": 0,
        })
        assert resp.status_code == 201
        assert len(resp.json()["details"]) == 1

    @pytest.mark.asyncio
    async def test_remove_detail_from_recipe(self, client, sample_material_id):
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "明細削除テスト",
            "waste_type": "焼却灰",
            "details": [
                {
                    "material_id": sample_material_id,
                    "material_type": "solidification",
                    "addition_rate": 100.0,
                },
            ],
        })
        rid = create_resp.json()["id"]
        detail_id = create_resp.json()["details"][0]["id"]
        resp = await client.delete(f"/api/v1/recipes/{rid}/details/{detail_id}")
        assert resp.status_code == 200
        # Verify detail was removed
        get_resp = await client.get(f"/api/v1/recipes/{rid}")
        assert len(get_resp.json()["details"]) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_removes_details(self, client, sample_material_id):
        """Deleting a recipe should also delete its details."""
        create_resp = await client.post("/api/v1/recipes", json={
            "name": "カスケード削除テスト",
            "waste_type": "汚泥（一般）",
            "details": [
                {
                    "material_id": sample_material_id,
                    "material_type": "solidification",
                    "addition_rate": 80.0,
                },
            ],
        })
        rid = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/recipes/{rid}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/api/v1/recipes/{rid}")
        assert get_resp.status_code == 404
