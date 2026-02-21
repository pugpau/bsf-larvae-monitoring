"""Integration tests for delivery API endpoints (incoming-materials + delivery-schedules)."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.database.postgresql import Base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


@pytest.fixture
async def api_session():
    """Fresh DB + session for integration tests."""
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

async def _create_supplier(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/suppliers", json={
        "name": "テスト業者",
        "waste_types": ["汚泥"],
        "is_active": True,
    })
    assert r.status_code == 201
    return r.json()


async def _create_material(client: AsyncClient, supplier_id: str) -> dict:
    r = await client.post("/api/v1/incoming-materials", json={
        "supplier_id": supplier_id,
        "material_category": "汚泥",
        "name": "A社汚泥",
        "default_weight_unit": "t",
        "is_active": True,
    })
    assert r.status_code == 201
    return r.json()


async def _create_schedule(
    client: AsyncClient,
    material_id: str,
    scheduled_date: str = "2026-03-01",
    **overrides,
) -> dict:
    payload = {
        "incoming_material_id": material_id,
        "scheduled_date": scheduled_date,
        "estimated_weight": 10.0,
        "weight_unit": "t",
        **overrides,
    }
    r = await client.post("/api/v1/delivery-schedules", json=payload)
    assert r.status_code == 201
    return r.json()


# ══════════════════════════════════════
#  Incoming Materials API
# ══════════════════════════════════════

class TestIncomingMaterialsCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        assert mat["name"] == "A社汚泥"
        assert mat["supplier_name"] == "テスト業者"

        r = await client.get(f"/api/v1/incoming-materials/{mat['id']}")
        assert r.status_code == 200
        assert r.json()["name"] == "A社汚泥"

    @pytest.mark.asyncio
    async def test_list(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get("/api/v1/incoming-materials")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    @pytest.mark.asyncio
    async def test_update(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        r = await client.put(
            f"/api/v1/incoming-materials/{mat['id']}",
            json={"name": "更新後の名前"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "更新後の名前"

    @pytest.mark.asyncio
    async def test_delete(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        r = await client.delete(f"/api/v1/incoming-materials/{mat['id']}")
        assert r.status_code == 204
        r2 = await client.get(f"/api/v1/incoming-materials/{mat['id']}")
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        r = await client.get("/api/v1/incoming-materials/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestIncomingMaterialsSearch:
    @pytest.mark.asyncio
    async def test_search_by_query(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get("/api/v1/incoming-materials", params={"q": "A社"})
        assert r.status_code == 200
        assert r.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get("/api/v1/incoming-materials", params={"material_category": "汚泥"})
        assert r.status_code == 200
        assert r.json()["total"] >= 1


class TestCascadingEndpoints:
    @pytest.mark.asyncio
    async def test_categories_by_supplier(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get(f"/api/v1/incoming-materials/categories/{sup['id']}")
        assert r.status_code == 200
        assert "汚泥" in r.json()

    @pytest.mark.asyncio
    async def test_materials_by_supplier(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get(f"/api/v1/incoming-materials/by-supplier/{sup['id']}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    @pytest.mark.asyncio
    async def test_materials_by_supplier_with_category(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get(
            f"/api/v1/incoming-materials/by-supplier/{sup['id']}",
            params={"category": "汚泥"},
        )
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestIncomingMaterialsCSV:
    @pytest.mark.asyncio
    async def test_export_csv(self, client):
        sup = await _create_supplier(client)
        await _create_material(client, sup["id"])
        r = await client.get("/api/v1/incoming-materials/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")


# ══════════════════════════════════════
#  Delivery Schedules API
# ══════════════════════════════════════

class TestDeliverySchedulesCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        assert sched["status"] == "scheduled"
        assert sched["supplier_name"] == "テスト業者"

        r = await client.get(f"/api/v1/delivery-schedules/{sched['id']}")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"])
        r = await client.get("/api/v1/delivery-schedules")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_update(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        r = await client.put(
            f"/api/v1/delivery-schedules/{sched['id']}",
            json={"notes": "更新メモ"},
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "更新メモ"

    @pytest.mark.asyncio
    async def test_delete(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        r = await client.delete(f"/api/v1/delivery-schedules/{sched['id']}")
        assert r.status_code == 204


class TestDeliveryStatusTransition:
    @pytest.mark.asyncio
    async def test_deliver(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        r = await client.put(
            f"/api/v1/delivery-schedules/{sched['id']}/status",
            json={"status": "delivered", "actual_weight": 8.5},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "delivered"
        assert body["actual_weight"] == 8.5
        assert body["waste_record_id"] is not None

    @pytest.mark.asyncio
    async def test_cancel(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        r = await client.put(
            f"/api/v1/delivery-schedules/{sched['id']}/status",
            json={"status": "cancelled"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_invalid_transition(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        sched = await _create_schedule(client, mat["id"])
        # First deliver
        await client.put(
            f"/api/v1/delivery-schedules/{sched['id']}/status",
            json={"status": "delivered"},
        )
        # Then try to cancel — should fail
        r = await client.put(
            f"/api/v1/delivery-schedules/{sched['id']}/status",
            json={"status": "cancelled"},
        )
        assert r.status_code == 400


class TestDeliveryScheduleDateFilter:
    """Integration tests for date_from/date_to query parameters on delivery-schedules API."""

    @pytest.mark.asyncio
    async def test_date_from_via_api(self, client):
        """GET /delivery-schedules?date_from=... excludes earlier records."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-02-28")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-15")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={"date_from": "2026-03-01"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        dates = {item["scheduled_date"] for item in body["items"]}
        assert "2026-02-28" not in dates

    @pytest.mark.asyncio
    async def test_date_to_via_api(self, client):
        """GET /delivery-schedules?date_to=... excludes later records."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-15")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-31")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={"date_to": "2026-03-15"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        dates = {item["scheduled_date"] for item in body["items"]}
        assert "2026-03-31" not in dates

    @pytest.mark.asyncio
    async def test_date_range_via_api(self, client):
        """GET /delivery-schedules?date_from=...&date_to=... returns only in-range records."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-02-28")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-07")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-08")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={"date_from": "2026-03-01", "date_to": "2026-03-07"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        dates = {item["scheduled_date"] for item in body["items"]}
        assert dates == {"2026-03-01", "2026-03-07"}

    @pytest.mark.asyncio
    async def test_date_range_empty_result(self, client):
        """Returns empty items when no schedules match the date range."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={"date_from": "2026-04-01", "date_to": "2026-04-30"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    @pytest.mark.asyncio
    async def test_date_range_with_status_filter(self, client):
        """date_from/date_to can be combined with status filter."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-15")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={
                "date_from": "2026-03-10",
                "date_to": "2026-03-31",
                "status": "scheduled",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["scheduled_date"] == "2026-03-15"

    @pytest.mark.asyncio
    async def test_date_range_with_sort_asc(self, client):
        """Calendar view typically sorts by scheduled_date asc."""
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-07")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-01")
        await _create_schedule(client, mat["id"], scheduled_date="2026-03-04")
        r = await client.get(
            "/api/v1/delivery-schedules",
            params={
                "date_from": "2026-03-01",
                "date_to": "2026-03-07",
                "sort_by": "scheduled_date",
                "sort_order": "asc",
            },
        )
        assert r.status_code == 200
        body = r.json()
        dates = [item["scheduled_date"] for item in body["items"]]
        assert dates == ["2026-03-01", "2026-03-04", "2026-03-07"]


class TestDeliverySchedulesCSV:
    @pytest.mark.asyncio
    async def test_export_csv(self, client):
        sup = await _create_supplier(client)
        mat = await _create_material(client, sup["id"])
        await _create_schedule(client, mat["id"])
        r = await client.get("/api/v1/delivery-schedules/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
