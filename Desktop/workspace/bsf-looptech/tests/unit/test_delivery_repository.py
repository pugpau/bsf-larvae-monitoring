"""Unit tests for incoming materials and delivery schedule repositories."""

import pytest

from src.materials.repository import SupplierRepository
from src.delivery.repository import (
    IncomingMaterialRepository,
    DeliveryScheduleRepository,
)


# ══════════════════════════════════════
#  Helpers — seed data
# ══════════════════════════════════════

async def _seed_supplier(session) -> dict:
    repo = SupplierRepository(session)
    return await repo.create({
        "name": "テスト搬入先",
        "contact_person": "担当A",
        "waste_types": ["汚泥"],
        "is_active": True,
    })


async def _seed_incoming_material(session, supplier_id: str, **overrides) -> dict:
    repo = IncomingMaterialRepository(session)
    data = {
        "supplier_id": supplier_id,
        "material_category": "汚泥",
        "name": "A社汚泥",
        "default_weight_unit": "t",
        "is_active": True,
        **overrides,
    }
    return await repo.create(data)


async def _seed_schedule(session, material_id: str, **overrides) -> dict:
    repo = DeliveryScheduleRepository(session)
    data = {
        "incoming_material_id": material_id,
        "scheduled_date": "2026-03-01",
        "estimated_weight": 10.0,
        "weight_unit": "t",
        "notes": "テスト予定",
        **overrides,
    }
    return await repo.create(data)


# ══════════════════════════════════════
#  IncomingMaterial Repository
# ══════════════════════════════════════

class TestIncomingMaterialCreate:
    @pytest.mark.asyncio
    async def test_create_success(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        assert mat is not None
        assert mat["name"] == "A社汚泥"
        assert mat["material_category"] == "汚泥"
        # supplier_name is enriched by get_by_id, not by _BaseRepository.create
        repo = IncomingMaterialRepository(async_session)
        enriched = await repo.get_by_id(mat["id"])
        assert enriched["supplier_name"] == "テスト搬入先"

    @pytest.mark.asyncio
    async def test_create_with_description(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(
            async_session, sup["id"], description="高含水率", notes="要注意"
        )
        assert mat["description"] == "高含水率"
        assert mat["notes"] == "要注意"


class TestIncomingMaterialGetAll:
    @pytest.mark.asyncio
    async def test_get_all_empty(self, async_session):
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all()
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_with_items(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="搬入物A")
        await _seed_incoming_material(async_session, sup["id"], name="搬入物B", material_category="焼却灰")
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all()
        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_search_by_name(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="特殊汚泥")
        await _seed_incoming_material(async_session, sup["id"], name="焼却灰A", material_category="焼却灰")
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all(q="特殊")
        assert total == 1
        assert items[0]["name"] == "特殊汚泥"

    @pytest.mark.asyncio
    async def test_filter_by_category(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="A", material_category="汚泥")
        await _seed_incoming_material(async_session, sup["id"], name="B", material_category="焼却灰")
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all(material_category="焼却灰")
        assert total == 1
        assert items[0]["material_category"] == "焼却灰"

    @pytest.mark.asyncio
    async def test_filter_by_supplier(self, async_session):
        sup1 = await _seed_supplier(async_session)
        sup_repo = SupplierRepository(async_session)
        sup2 = await sup_repo.create({"name": "搬入先B", "waste_types": [], "is_active": True})
        await _seed_incoming_material(async_session, sup1["id"], name="A")
        await _seed_incoming_material(async_session, sup2["id"], name="B")
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all(supplier_id=sup1["id"])
        assert total == 1
        assert items[0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_pagination(self, async_session):
        sup = await _seed_supplier(async_session)
        for i in range(5):
            await _seed_incoming_material(async_session, sup["id"], name=f"搬入物{i}")
        repo = IncomingMaterialRepository(async_session)
        items, total = await repo.get_all(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2


class TestIncomingMaterialGetById:
    @pytest.mark.asyncio
    async def test_get_by_id(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        repo = IncomingMaterialRepository(async_session)
        result = await repo.get_by_id(mat["id"])
        assert result is not None
        assert result["id"] == mat["id"]
        assert result["supplier_name"] == "テスト搬入先"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, async_session):
        repo = IncomingMaterialRepository(async_session)
        result = await repo.get_by_id("00000000-0000-0000-0000-000000000000")
        assert result is None


class TestIncomingMaterialUpdate:
    @pytest.mark.asyncio
    async def test_update(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        repo = IncomingMaterialRepository(async_session)
        result = await repo.update(mat["id"], {"name": "更新後"})
        assert result["name"] == "更新後"


class TestIncomingMaterialDelete:
    @pytest.mark.asyncio
    async def test_delete(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        repo = IncomingMaterialRepository(async_session)
        deleted = await repo.delete(mat["id"])
        assert deleted is True
        result = await repo.get_by_id(mat["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, async_session):
        repo = IncomingMaterialRepository(async_session)
        deleted = await repo.delete("00000000-0000-0000-0000-000000000000")
        assert deleted is False


class TestCascadingHelpers:
    @pytest.mark.asyncio
    async def test_get_categories_by_supplier(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="A", material_category="汚泥")
        await _seed_incoming_material(async_session, sup["id"], name="B", material_category="焼却灰")
        await _seed_incoming_material(async_session, sup["id"], name="C", material_category="汚泥")
        repo = IncomingMaterialRepository(async_session)
        cats = await repo.get_categories_by_supplier(sup["id"])
        assert set(cats) == {"汚泥", "焼却灰"}

    @pytest.mark.asyncio
    async def test_get_by_supplier_and_category(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="A", material_category="汚泥")
        await _seed_incoming_material(async_session, sup["id"], name="B", material_category="焼却灰")
        repo = IncomingMaterialRepository(async_session)
        items = await repo.get_by_supplier_and_category(sup["id"], "汚泥")
        assert len(items) == 1
        assert items[0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_get_by_supplier_no_category_filter(self, async_session):
        sup = await _seed_supplier(async_session)
        await _seed_incoming_material(async_session, sup["id"], name="A", material_category="汚泥")
        await _seed_incoming_material(async_session, sup["id"], name="B", material_category="焼却灰")
        repo = IncomingMaterialRepository(async_session)
        items = await repo.get_by_supplier_and_category(sup["id"])
        assert len(items) == 2


# ══════════════════════════════════════
#  DeliverySchedule Repository
# ══════════════════════════════════════

class TestDeliveryScheduleCreate:
    @pytest.mark.asyncio
    async def test_create_success(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        sched = await _seed_schedule(async_session, mat["id"])
        assert sched is not None
        assert sched["status"] == "scheduled"
        assert sched["supplier_name"] == "テスト搬入先"
        assert sched["material_name"] == "A社汚泥"
        assert sched["material_category"] == "汚泥"


class TestDeliveryScheduleGetAll:
    @pytest.mark.asyncio
    async def test_get_all_empty(self, async_session):
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all()
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_with_items(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-02")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all()
        assert total == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"])
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(status="scheduled")
        assert total == 1
        items2, total2 = await repo.get_all(status="delivered")
        assert total2 == 0

    @pytest.mark.asyncio
    async def test_pagination(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        for i in range(5):
            await _seed_schedule(async_session, mat["id"], scheduled_date=f"2026-03-{i+1:02d}")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2


class TestDeliveryScheduleUpdate:
    @pytest.mark.asyncio
    async def test_update(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        sched = await _seed_schedule(async_session, mat["id"])
        repo = DeliveryScheduleRepository(async_session)
        result = await repo.update(sched["id"], {"notes": "更新テスト"})
        assert result["notes"] == "更新テスト"

    @pytest.mark.asyncio
    async def test_update_not_found(self, async_session):
        repo = DeliveryScheduleRepository(async_session)
        result = await repo.update("00000000-0000-0000-0000-000000000000", {"notes": "x"})
        assert result is None


class TestDeliveryScheduleDelete:
    @pytest.mark.asyncio
    async def test_delete(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        sched = await _seed_schedule(async_session, mat["id"])
        repo = DeliveryScheduleRepository(async_session)
        deleted = await repo.delete(sched["id"])
        assert deleted is True
        result = await repo.get_by_id(sched["id"])
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, async_session):
        repo = DeliveryScheduleRepository(async_session)
        deleted = await repo.delete("00000000-0000-0000-0000-000000000000")
        assert deleted is False


class TestDeliveryScheduleDateFilter:
    """Tests for date_from / date_to filtering on DeliveryScheduleRepository.get_all()."""

    @pytest.mark.asyncio
    async def test_date_from_filters_earlier_dates(self, async_session):
        """Schedules before date_from are excluded."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-02-28")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-15")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(date_from="2026-03-01")
        assert total == 2
        dates = {item["scheduled_date"] for item in items}
        assert "2026-02-28" not in dates
        assert "2026-03-01" in dates
        assert "2026-03-15" in dates

    @pytest.mark.asyncio
    async def test_date_to_filters_later_dates(self, async_session):
        """Schedules after date_to are excluded."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-15")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-31")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(date_to="2026-03-15")
        assert total == 2
        dates = {item["scheduled_date"] for item in items}
        assert "2026-03-01" in dates
        assert "2026-03-15" in dates
        assert "2026-03-31" not in dates

    @pytest.mark.asyncio
    async def test_date_from_and_date_to_combined(self, async_session):
        """Only schedules within the date_from..date_to range are returned."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-02-28")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-07")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-08")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(date_from="2026-03-01", date_to="2026-03-07")
        assert total == 2
        dates = {item["scheduled_date"] for item in items}
        assert dates == {"2026-03-01", "2026-03-07"}

    @pytest.mark.asyncio
    async def test_date_from_same_as_date_to_single_day(self, async_session):
        """When date_from equals date_to, only that single day is returned."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-02")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(date_from="2026-03-01", date_to="2026-03-01")
        assert total == 1
        assert items[0]["scheduled_date"] == "2026-03-01"

    @pytest.mark.asyncio
    async def test_date_range_no_matches(self, async_session):
        """Returns empty when no schedules fall in the date range."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(date_from="2026-04-01", date_to="2026-04-30")
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_date_from_with_status_filter_combined(self, async_session):
        """date_from and status filters can be combined."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        # Seed two scheduled, one on different dates
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-01")
        await _seed_schedule(async_session, mat["id"], scheduled_date="2026-03-15")
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(
            date_from="2026-03-10",
            status="scheduled",
        )
        assert total == 1
        assert items[0]["scheduled_date"] == "2026-03-15"

    @pytest.mark.asyncio
    async def test_date_range_with_text_search(self, async_session):
        """date_from/date_to combined with text search (q parameter)."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(
            async_session, mat["id"],
            scheduled_date="2026-03-01", notes="重要な搬入",
        )
        await _seed_schedule(
            async_session, mat["id"],
            scheduled_date="2026-03-01", notes="通常の搬入",
        )
        await _seed_schedule(
            async_session, mat["id"],
            scheduled_date="2026-04-01", notes="重要な搬入",
        )
        repo = DeliveryScheduleRepository(async_session)
        items, total = await repo.get_all(
            date_from="2026-03-01", date_to="2026-03-31", q="重要",
        )
        assert total == 1
        assert items[0]["notes"] == "重要な搬入"
        assert items[0]["scheduled_date"] == "2026-03-01"

    @pytest.mark.asyncio
    async def test_date_range_count_matches_items(self, async_session):
        """The returned total count is consistent with the items list length."""
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        for day in range(1, 8):
            await _seed_schedule(
                async_session, mat["id"],
                scheduled_date=f"2026-03-{day:02d}",
            )
        repo = DeliveryScheduleRepository(async_session)
        # Request week range but with limit smaller than total
        items, total = await repo.get_all(
            date_from="2026-03-01", date_to="2026-03-07",
            limit=3, offset=0,
        )
        assert total == 7
        assert len(items) == 3


class TestDeliveryScheduleExport:
    @pytest.mark.asyncio
    async def test_export(self, async_session):
        sup = await _seed_supplier(async_session)
        mat = await _seed_incoming_material(async_session, sup["id"])
        await _seed_schedule(async_session, mat["id"])
        repo = DeliveryScheduleRepository(async_session)
        items = await repo.get_all_for_export()
        assert len(items) == 1
        assert items[0]["supplier_name"] == "テスト搬入先"
