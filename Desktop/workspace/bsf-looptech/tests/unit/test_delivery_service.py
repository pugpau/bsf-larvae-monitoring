"""Unit tests for delivery service (status transitions + WasteRecord creation)."""

import pytest

from src.materials.repository import SupplierRepository
from src.delivery.repository import (
    IncomingMaterialRepository,
    DeliveryScheduleRepository,
)
from src.delivery.service import DeliveryService, VALID_TRANSITIONS
from src.waste.repository import WasteRepository


# ══════════════════════════════════════
#  Helpers
# ══════════════════════════════════════

async def _setup(session):
    """Create supplier + incoming material + delivery schedule, return IDs."""
    sup = await SupplierRepository(session).create({
        "name": "テスト業者",
        "waste_types": ["汚泥"],
        "is_active": True,
    })
    mat = await IncomingMaterialRepository(session).create({
        "supplier_id": sup["id"],
        "material_category": "汚泥",
        "name": "A社汚泥",
        "default_weight_unit": "t",
        "is_active": True,
    })
    sched = await DeliveryScheduleRepository(session).create({
        "incoming_material_id": mat["id"],
        "scheduled_date": "2026-03-01",
        "estimated_weight": 10.0,
        "weight_unit": "t",
    })
    return sup, mat, sched


def _make_service(session):
    return DeliveryService(
        session=session,
        schedule_repo=DeliveryScheduleRepository(session),
        waste_repo=WasteRepository(session),
    )


# ══════════════════════════════════════
#  Status Transition Tests
# ══════════════════════════════════════

class TestValidTransitions:
    def test_scheduled_can_transition_to_delivered(self):
        assert "delivered" in VALID_TRANSITIONS["scheduled"]

    def test_scheduled_can_transition_to_cancelled(self):
        assert "cancelled" in VALID_TRANSITIONS["scheduled"]

    def test_delivered_is_terminal(self):
        assert "delivered" not in VALID_TRANSITIONS


class TestUpdateStatusDelivered:
    @pytest.mark.asyncio
    async def test_deliver_creates_waste_record(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        result = await service.update_status(sched["id"], "delivered", actual_weight=8.5)
        assert result is not None
        assert result["status"] == "delivered"
        assert result["actual_weight"] == 8.5
        assert result["waste_record_id"] is not None

    @pytest.mark.asyncio
    async def test_deliver_without_actual_weight_uses_estimated(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        result = await service.update_status(sched["id"], "delivered")
        assert result["actual_weight"] == 10.0  # estimated_weight

    @pytest.mark.asyncio
    async def test_deliver_waste_record_has_correct_data(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        result = await service.update_status(sched["id"], "delivered", actual_weight=5.0)
        # Verify the linked waste record exists
        waste_repo = WasteRepository(async_session)
        wr = await waste_repo.get_by_id(result["waste_record_id"])
        assert wr is not None
        assert wr["source"] == "テスト業者"
        assert wr["wasteType"] == "汚泥"
        assert wr["weight"] == 5.0
        assert wr["status"] == "pending"
        assert "搬入予定より自動登録" in wr["notes"]


class TestUpdateStatusCancelled:
    @pytest.mark.asyncio
    async def test_cancel_success(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        result = await service.update_status(sched["id"], "cancelled")
        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_no_waste_record(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        result = await service.update_status(sched["id"], "cancelled")
        assert result["waste_record_id"] is None


class TestUpdateStatusRejected:
    @pytest.mark.asyncio
    async def test_delivered_cannot_change(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        await service.update_status(sched["id"], "delivered")
        with pytest.raises(ValueError, match="Cannot transition"):
            await service.update_status(sched["id"], "cancelled")

    @pytest.mark.asyncio
    async def test_cancelled_cannot_change(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        await service.update_status(sched["id"], "cancelled")
        with pytest.raises(ValueError, match="Cannot transition"):
            await service.update_status(sched["id"], "delivered")

    @pytest.mark.asyncio
    async def test_invalid_status(self, async_session):
        _, _, sched = await _setup(async_session)
        service = _make_service(async_session)
        with pytest.raises(ValueError, match="Cannot transition"):
            await service.update_status(sched["id"], "invalid_status")


class TestUpdateStatusNotFound:
    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, async_session):
        service = _make_service(async_session)
        result = await service.update_status(
            "00000000-0000-0000-0000-000000000000", "delivered"
        )
        assert result is None
