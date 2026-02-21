"""Unit tests for formulation record repository."""

import pytest

from src.formulation.repository import FormulationRecordRepository, VALID_TRANSITIONS
from src.waste.repository import WasteRepository


# ══════════════════════════════════════
#  Helpers — seed data
# ══════════════════════════════════════

async def _seed_waste_record(session, **overrides) -> dict:
    repo = WasteRepository(session)
    data = {
        "source": "テスト業者",
        "deliveryDate": "2026-03-01",
        "wasteType": "汚泥（一般）",
        "weight": 10.0,
        "weightUnit": "t",
        "status": "pending",
        "analysis": {"pH": 7.0, "moisture": 40.0, "Pb": 0.005},
        **overrides,
    }
    return await repo.create(data)


async def _seed_formulation(session, waste_record_id: str, **overrides) -> dict:
    repo = FormulationRecordRepository(session)
    data = {
        "waste_record_id": waste_record_id,
        "source_type": "ml",
        "planned_formulation": {
            "solidifierType": "普通ポルトランドセメント",
            "solidifierAmount": 150.0,
            "solidifierUnit": "kg/t",
        },
        "confidence": 0.85,
        "reasoning": ["ML予測", "分類精度: 0.85"],
        **overrides,
    }
    return await repo.create(data)


# ══════════════════════════════════════
#  Valid Transitions
# ══════════════════════════════════════

class TestValidTransitions:
    def test_proposed_can_accept(self):
        assert "accepted" in VALID_TRANSITIONS["proposed"]

    def test_proposed_can_reject(self):
        assert "rejected" in VALID_TRANSITIONS["proposed"]

    def test_accepted_can_apply(self):
        assert "applied" in VALID_TRANSITIONS["accepted"]

    def test_applied_can_verify(self):
        assert "verified" in VALID_TRANSITIONS["applied"]

    def test_verified_is_terminal(self):
        assert "verified" not in VALID_TRANSITIONS

    def test_rejected_is_terminal(self):
        assert "rejected" not in VALID_TRANSITIONS


# ══════════════════════════════════════
#  Create
# ══════════════════════════════════════

class TestCreate:
    @pytest.mark.asyncio
    async def test_create_success(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        assert record is not None
        assert record["status"] == "proposed"
        assert record["source_type"] == "ml"
        assert record["confidence"] == 0.85
        assert record["waste_type"] == "汚泥（一般）"

    @pytest.mark.asyncio
    async def test_create_manual(self, async_session):
        waste = await _seed_waste_record(async_session)
        repo = FormulationRecordRepository(async_session)
        record = await repo.create({
            "waste_record_id": waste["id"],
            "source_type": "manual",
            "planned_formulation": {"solidifierAmount": 200.0},
            "notes": "手動入力",
        })
        assert record["source_type"] == "manual"
        assert record["notes"] == "手動入力"


# ══════════════════════════════════════
#  Get
# ══════════════════════════════════════

class TestGet:
    @pytest.mark.asyncio
    async def test_get_by_id(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        fetched = await repo.get_by_id(record["id"])
        assert fetched is not None
        assert fetched["id"] == record["id"]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, async_session):
        repo = FormulationRecordRepository(async_session)
        result = await repo.get_by_id("00000000-0000-0000-0000-000000000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_waste_record(self, async_session):
        waste = await _seed_waste_record(async_session)
        await _seed_formulation(async_session, waste["id"], source_type="ml")
        await _seed_formulation(async_session, waste["id"], source_type="rule")
        repo = FormulationRecordRepository(async_session)
        items = await repo.get_by_waste_record(waste["id"])
        assert len(items) == 2


# ══════════════════════════════════════
#  Get All (pagination + filters)
# ══════════════════════════════════════

class TestGetAll:
    @pytest.mark.asyncio
    async def test_get_all_empty(self, async_session):
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all()
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_all_with_items(self, async_session):
        waste = await _seed_waste_record(async_session)
        await _seed_formulation(async_session, waste["id"])
        await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all()
        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_filter_by_waste_record_id(self, async_session):
        w1 = await _seed_waste_record(async_session)
        w2 = await _seed_waste_record(async_session, source="別の業者")
        await _seed_formulation(async_session, w1["id"])
        await _seed_formulation(async_session, w2["id"])
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all(waste_record_id=w1["id"])
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_by_status(self, async_session):
        waste = await _seed_waste_record(async_session)
        await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all(status="proposed")
        assert total == 1
        items2, total2 = await repo.get_all(status="accepted")
        assert total2 == 0

    @pytest.mark.asyncio
    async def test_filter_by_source_type(self, async_session):
        waste = await _seed_waste_record(async_session)
        await _seed_formulation(async_session, waste["id"], source_type="ml")
        await _seed_formulation(async_session, waste["id"], source_type="rule")
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all(source_type="ml")
        assert total == 1

    @pytest.mark.asyncio
    async def test_pagination(self, async_session):
        waste = await _seed_waste_record(async_session)
        for _ in range(5):
            await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        items, total = await repo.get_all(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2


# ══════════════════════════════════════
#  Update
# ══════════════════════════════════════

class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_notes(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        updated = await repo.update(record["id"], {"notes": "更新済み"})
        assert updated is not None
        assert updated["notes"] == "更新済み"

    @pytest.mark.asyncio
    async def test_update_planned_formulation(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        new_form = {"solidifierAmount": 200.0}
        updated = await repo.update(record["id"], {"planned_formulation": new_form})
        assert updated["planned_formulation"]["solidifierAmount"] == 200.0

    @pytest.mark.asyncio
    async def test_update_not_found(self, async_session):
        repo = FormulationRecordRepository(async_session)
        result = await repo.update("00000000-0000-0000-0000-000000000000", {"notes": "x"})
        assert result is None


# ══════════════════════════════════════
#  Status Transitions
# ══════════════════════════════════════

class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_proposed_to_accepted(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        result = await repo.transition_status(record["id"], "accepted")
        assert result["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_accepted_to_applied(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        await repo.transition_status(record["id"], "accepted")
        result = await repo.transition_status(record["id"], "applied", {
            "actual_formulation": {"solidifierAmount": 160.0},
        })
        assert result["status"] == "applied"
        assert result["actual_formulation"]["solidifierAmount"] == 160.0

    @pytest.mark.asyncio
    async def test_applied_to_verified(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        await repo.transition_status(record["id"], "accepted")
        await repo.transition_status(record["id"], "applied")
        result = await repo.transition_status(record["id"], "verified", {
            "elution_result": {"Pb": 0.003, "As": 0.002},
            "elution_passed": True,
        })
        assert result["status"] == "verified"
        assert result["elution_passed"] is True

    @pytest.mark.asyncio
    async def test_proposed_to_rejected(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        result = await repo.transition_status(record["id"], "rejected", {
            "notes": "コスト超過のため却下",
        })
        assert result["status"] == "rejected"
        assert result["notes"] == "コスト超過のため却下"

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        with pytest.raises(ValueError, match="Cannot transition"):
            await repo.transition_status(record["id"], "verified")

    @pytest.mark.asyncio
    async def test_transition_not_found(self, async_session):
        repo = FormulationRecordRepository(async_session)
        result = await repo.transition_status(
            "00000000-0000-0000-0000-000000000000", "accepted"
        )
        assert result is None


# ══════════════════════════════════════
#  Delete
# ══════════════════════════════════════

class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_proposed(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        assert await repo.delete(record["id"]) is True
        assert await repo.get_by_id(record["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_rejected(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        await repo.transition_status(record["id"], "rejected")
        assert await repo.delete(record["id"]) is True

    @pytest.mark.asyncio
    async def test_delete_accepted_raises(self, async_session):
        waste = await _seed_waste_record(async_session)
        record = await _seed_formulation(async_session, waste["id"])
        repo = FormulationRecordRepository(async_session)
        await repo.transition_status(record["id"], "accepted")
        with pytest.raises(ValueError, match="Cannot delete"):
            await repo.delete(record["id"])

    @pytest.mark.asyncio
    async def test_delete_not_found(self, async_session):
        repo = FormulationRecordRepository(async_session)
        assert await repo.delete("00000000-0000-0000-0000-000000000000") is False
