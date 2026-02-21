"""Integration tests for Phase 1 materials API (suppliers, solidification, suppressants)."""

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


# ══════════════════════════════════════
#  Suppliers
# ══════════════════════════════════════

class TestSupplierEndpoints:

    @pytest.mark.asyncio
    async def test_create_supplier(self, client):
        resp = await client.post("/api/v1/suppliers", json={
            "name": "テスト搬入先A",
            "contact_person": "山田太郎",
            "phone": "03-1234-5678",
            "waste_types": ["汚泥", "焼却灰"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "テスト搬入先A"
        assert data["waste_types"] == ["汚泥", "焼却灰"]
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_suppliers(self, client):
        await client.post("/api/v1/suppliers", json={"name": "搬入先B"})
        resp = await client.get("/api/v1/suppliers")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    @pytest.mark.asyncio
    async def test_get_supplier_by_id(self, client):
        create_resp = await client.post("/api/v1/suppliers", json={"name": "搬入先C"})
        sid = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/suppliers/{sid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "搬入先C"

    @pytest.mark.asyncio
    async def test_update_supplier(self, client):
        create_resp = await client.post("/api/v1/suppliers", json={"name": "旧名称"})
        sid = create_resp.json()["id"]
        resp = await client.put(f"/api/v1/suppliers/{sid}", json={"name": "新名称"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名称"

    @pytest.mark.asyncio
    async def test_delete_supplier(self, client):
        create_resp = await client.post("/api/v1/suppliers", json={"name": "削除対象"})
        sid = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/suppliers/{sid}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/api/v1/suppliers/{sid}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_supplier_not_found(self, client):
        resp = await client.get("/api/v1/suppliers/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ══════════════════════════════════════
#  Solidification Materials
# ══════════════════════════════════════

class TestSolidificationMaterialEndpoints:

    @pytest.mark.asyncio
    async def test_create_solidification_material(self, client):
        resp = await client.post("/api/v1/solidification-materials", json={
            "name": "普通ポルトランドセメント",
            "material_type": "cement",
            "base_material": "CaO-SiO2系",
            "min_addition_rate": 5.0,
            "max_addition_rate": 20.0,
            "unit_cost": 15.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "普通ポルトランドセメント"
        assert data["material_type"] == "cement"

    @pytest.mark.asyncio
    async def test_list_solidification_materials(self, client):
        await client.post("/api/v1/solidification-materials", json={
            "name": "消石灰",
            "material_type": "calcium",
        })
        resp = await client.get("/api/v1/solidification-materials")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    @pytest.mark.asyncio
    async def test_filter_by_material_type(self, client):
        await client.post("/api/v1/solidification-materials", json={
            "name": "高炉セメントB種",
            "material_type": "cement",
        })
        resp = await client.get("/api/v1/solidification-materials?material_type=cement")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_solidification_material(self, client):
        create_resp = await client.post("/api/v1/solidification-materials", json={
            "name": "削除固化材",
            "material_type": "other",
        })
        sid = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/solidification-materials/{sid}")
        assert resp.status_code == 200


# ══════════════════════════════════════
#  Leaching Suppressants
# ══════════════════════════════════════

class TestLeachingSuppressantEndpoints:

    @pytest.mark.asyncio
    async def test_create_leaching_suppressant(self, client):
        resp = await client.post("/api/v1/leaching-suppressants", json={
            "name": "キレート剤X",
            "suppressant_type": "chelate",
            "target_metals": ["Pb", "Cd", "As"],
            "min_addition_rate": 0.5,
            "max_addition_rate": 3.0,
            "ph_range_min": 7.0,
            "ph_range_max": 12.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "キレート剤X"
        assert "Pb" in data["target_metals"]

    @pytest.mark.asyncio
    async def test_list_leaching_suppressants(self, client):
        await client.post("/api/v1/leaching-suppressants", json={
            "name": "硫化物系Y",
            "suppressant_type": "sulfide",
            "target_metals": ["Hg"],
        })
        resp = await client.get("/api/v1/leaching-suppressants")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_leaching_suppressant(self, client):
        create_resp = await client.post("/api/v1/leaching-suppressants", json={
            "name": "更新用Z",
            "suppressant_type": "phosphate",
        })
        sid = create_resp.json()["id"]
        resp = await client.put(f"/api/v1/leaching-suppressants/{sid}", json={
            "max_addition_rate": 5.0,
        })
        assert resp.status_code == 200
        assert resp.json()["max_addition_rate"] == 5.0

    @pytest.mark.asyncio
    async def test_delete_leaching_suppressant(self, client):
        create_resp = await client.post("/api/v1/leaching-suppressants", json={
            "name": "削除抑制剤",
            "suppressant_type": "other",
        })
        sid = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/leaching-suppressants/{sid}")
        assert resp.status_code == 200
