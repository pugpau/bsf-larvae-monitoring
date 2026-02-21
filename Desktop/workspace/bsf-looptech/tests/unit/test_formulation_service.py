"""Unit tests for formulation workflow service."""

import pytest

from src.formulation.repository import FormulationRecordRepository
from src.formulation.service import FormulationWorkflowService
from src.waste.repository import WasteRepository


# ══════════════════════════════════════
#  Helpers
# ══════════════════════════════════════

async def _seed_waste(session, **overrides) -> dict:
    repo = WasteRepository(session)
    data = {
        "source": "テスト業者",
        "deliveryDate": "2026-03-01",
        "wasteType": "汚泥（一般）",
        "weight": 10.0,
        "weightUnit": "t",
        "status": "pending",
        "analysis": {
            "pH": 7.0,
            "moisture": 40.0,
            "ignitionLoss": 15.0,
            "Pb": 0.005,
            "As": 0.002,
            "Cd": 0.001,
            "Cr6": 0.01,
            "Hg": 0.0001,
            "Se": 0.003,
            "F": 0.3,
            "B": 0.2,
        },
        **overrides,
    }
    return await repo.create(data)


async def _seed_and_propose(session) -> tuple:
    """Seed waste + create proposed formulation, return (waste, formulation)."""
    waste = await _seed_waste(session)
    repo = FormulationRecordRepository(session)
    formulation = await repo.create({
        "waste_record_id": waste["id"],
        "source_type": "manual",
        "planned_formulation": {"solidifierAmount": 150.0},
    })
    return waste, formulation


# ══════════════════════════════════════
#  Accept
# ══════════════════════════════════════

class TestAccept:
    @pytest.mark.asyncio
    async def test_accept_proposed(self, async_session):
        _, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        result = await service.accept(formulation["id"])
        assert result is not None
        assert result["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_accept_not_found(self, async_session):
        service = FormulationWorkflowService(async_session)
        result = await service.accept("00000000-0000-0000-0000-000000000000")
        assert result is None


# ══════════════════════════════════════
#  Apply
# ══════════════════════════════════════

class TestApply:
    @pytest.mark.asyncio
    async def test_apply_updates_waste_record(self, async_session):
        waste, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        result = await service.apply_formulation(
            formulation["id"],
            actual_formulation={"solidifierAmount": 160.0},
            actual_cost=2400.0,
        )
        assert result is not None
        assert result["status"] == "applied"
        assert result["actual_formulation"]["solidifierAmount"] == 160.0
        assert result["actual_cost"] == 2400.0

        # Check waste record was updated
        waste_repo = WasteRepository(async_session)
        updated_waste = await waste_repo.get_by_id(waste["id"])
        assert updated_waste["formulation"] is not None
        assert updated_waste["status"] == "formulated"

    @pytest.mark.asyncio
    async def test_apply_uses_planned_if_no_actual(self, async_session):
        waste, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        result = await service.apply_formulation(formulation["id"])
        assert result["status"] == "applied"

        waste_repo = WasteRepository(async_session)
        updated_waste = await waste_repo.get_by_id(waste["id"])
        assert updated_waste["formulation"]["solidifierAmount"] == 150.0


# ══════════════════════════════════════
#  Verify
# ══════════════════════════════════════

class TestVerify:
    @pytest.mark.asyncio
    async def test_verify_passed_completes_waste(self, async_session):
        waste, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        await service.apply_formulation(formulation["id"])
        result = await service.verify(
            formulation["id"],
            elution_result={"Pb": 0.003, "As": 0.001},
            elution_passed=True,
            notes="溶出試験合格",
        )
        assert result is not None
        assert result["status"] == "verified"
        assert result["elution_passed"] is True

        waste_repo = WasteRepository(async_session)
        updated_waste = await waste_repo.get_by_id(waste["id"])
        assert updated_waste["status"] == "completed"

    @pytest.mark.asyncio
    async def test_verify_failed_sets_waste_failed(self, async_session):
        waste, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        await service.apply_formulation(formulation["id"])
        result = await service.verify(
            formulation["id"],
            elution_result={"Pb": 0.02},
            elution_passed=False,
        )
        assert result["elution_passed"] is False

        waste_repo = WasteRepository(async_session)
        updated_waste = await waste_repo.get_by_id(waste["id"])
        assert updated_waste["status"] == "failed"


# ══════════════════════════════════════
#  Reject
# ══════════════════════════════════════

class TestReject:
    @pytest.mark.asyncio
    async def test_reject_proposed(self, async_session):
        _, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        result = await service.reject(formulation["id"], notes="不採用")
        assert result["status"] == "rejected"
        assert result["notes"] == "不採用"

    @pytest.mark.asyncio
    async def test_reject_accepted(self, async_session):
        _, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        result = await service.reject(formulation["id"])
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_applied(self, async_session):
        _, formulation = await _seed_and_propose(async_session)
        service = FormulationWorkflowService(async_session)
        await service.accept(formulation["id"])
        await service.apply_formulation(formulation["id"])
        result = await service.reject(formulation["id"])
        assert result["status"] == "rejected"


# ══════════════════════════════════════
#  Recommend (basic — no ML models loaded)
# ══════════════════════════════════════

class TestRecommend:
    @pytest.mark.asyncio
    async def test_recommend_creates_candidates(self, async_session):
        waste = await _seed_waste(async_session)
        service = FormulationWorkflowService(async_session)
        candidates = await service.recommend(waste["id"], top_k=3)
        # Should get at least 1 candidate (rule-based fallback)
        assert len(candidates) >= 1
        assert candidates[0]["status"] == "proposed"
        assert candidates[0]["waste_record_id"] == waste["id"]

    @pytest.mark.asyncio
    async def test_recommend_no_analysis_raises(self, async_session):
        waste = await _seed_waste(async_session, analysis=None)
        service = FormulationWorkflowService(async_session)
        with pytest.raises(ValueError, match="no analysis data"):
            await service.recommend(waste["id"])

    @pytest.mark.asyncio
    async def test_recommend_not_found_raises(self, async_session):
        service = FormulationWorkflowService(async_session)
        with pytest.raises(ValueError, match="not found"):
            await service.recommend("00000000-0000-0000-0000-000000000000")


# ══════════════════════════════════════
#  Full Workflow (end-to-end unit)
# ══════════════════════════════════════

class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_propose_accept_apply_verify(self, async_session):
        """Complete happy path: proposed → accepted → applied → verified."""
        waste = await _seed_waste(async_session)
        service = FormulationWorkflowService(async_session)

        # 1. Create manual proposal
        repo = FormulationRecordRepository(async_session)
        formulation = await repo.create({
            "waste_record_id": waste["id"],
            "source_type": "manual",
            "planned_formulation": {
                "solidifierType": "普通ポルトランドセメント",
                "solidifierAmount": 150.0,
            },
        })
        assert formulation["status"] == "proposed"

        # 2. Accept
        accepted = await service.accept(formulation["id"])
        assert accepted["status"] == "accepted"

        # 3. Apply
        applied = await service.apply_formulation(
            formulation["id"],
            actual_formulation={
                "solidifierType": "普通ポルトランドセメント",
                "solidifierAmount": 160.0,
            },
        )
        assert applied["status"] == "applied"

        # 4. Verify
        verified = await service.verify(
            formulation["id"],
            elution_result={"Pb": 0.002, "As": 0.001, "Cd": 0.0005},
            elution_passed=True,
        )
        assert verified["status"] == "verified"
        assert verified["elution_passed"] is True

        # Check final waste record state
        waste_repo = WasteRepository(async_session)
        final_waste = await waste_repo.get_by_id(waste["id"])
        assert final_waste["status"] == "completed"
        assert final_waste["elutionResult"] is not None
