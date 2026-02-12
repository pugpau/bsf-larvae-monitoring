"""Unit tests for KPI service."""

import uuid
from datetime import datetime, timedelta

import pytest

from src.database.postgresql import (
    LeachingSuppressant,
    MLPrediction,
    SolidificationMaterial,
    WasteRecord,
)
from src.kpi.service import KPIService


@pytest.mark.asyncio
class TestKPIRealtime:
    """Tests for KPIService.get_realtime()."""

    async def test_empty_db(self, async_session):
        """All KPIs should be zero/neutral with no data."""
        service = KPIService(async_session)
        result = await service.get_realtime(days=7)

        assert result["processing_volume"]["value"] == 0
        assert result["formulation_success_rate"]["value"] == 0.0
        assert result["material_cost"]["value"] == 0.0
        assert result["ml_usage_rate"]["value"] == 0.0
        assert result["avg_processing_time"]["value"] == 0.0
        assert result["violation_rate"]["value"] == 0.0
        assert result["period_days"] == 7
        assert "updated_at" in result

    async def test_processing_volume(self, async_session):
        """Should count records in the period, excluding old ones."""
        for i in range(3):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=12),
                waste_type="汚泥",
                status="pending",
            ))
        # Old record — outside 7-day window
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="old",
            delivery_date=datetime.utcnow() - timedelta(days=30),
            waste_type="汚泥",
            status="pending",
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        assert result["processing_volume"]["value"] == 3

    async def test_formulation_success_rate(self, async_session):
        """Should calculate success ratio correctly."""
        statuses = ["formulated", "formulated", "pending", "tested"]
        for i, status in enumerate(statuses):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=12),
                waste_type="汚泥",
                status=status,
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        # 3 successes (formulated*2 + tested) out of 4
        assert result["formulation_success_rate"]["value"] == 75.0
        assert result["formulation_success_rate"]["status"] == "normal"

    async def test_success_rate_warning(self, async_session):
        """Should set warning status when success rate < 70%."""
        # 2 pending, 1 formulated → 33.3% → critical
        for i, status in enumerate(["pending", "pending", "formulated"]):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=6),
                waste_type="汚泥",
                status=status,
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        assert result["formulation_success_rate"]["status"] == "critical"

    async def test_ml_usage_rate(self, async_session):
        """Should calculate ml_predictions / waste_records ratio."""
        for i in range(4):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=12),
                waste_type="汚泥",
                status="formulated",
            ))
        for i in range(2):
            async_session.add(MLPrediction(
                id=uuid.uuid4(),
                method="ml",
                input_features={},
                prediction={},
                confidence=0.9,
                created_at=datetime.utcnow() - timedelta(hours=6),
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        assert result["ml_usage_rate"]["value"] == 50.0

    async def test_violation_rate(self, async_session):
        """Should detect elution violations."""
        # 1 passing
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="OK工場",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="tested",
            elution_result={"Pb": 0.005, "As": 0.001},
        ))
        # 1 failing (Pb exceeds 0.01)
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="NG工場",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="tested",
            elution_result={"Pb": 0.05, "As": 0.001},
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        assert result["violation_rate"]["value"] == 50.0
        assert result["violation_rate"]["status"] == "critical"

    async def test_avg_processing_time(self, async_session):
        """Should compute average delivery_date to updated_at delta."""
        now = datetime.utcnow()
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="工場A",
            delivery_date=now - timedelta(hours=48),
            waste_type="汚泥",
            status="formulated",
            updated_at=now,
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        # Should be approximately 48 hours
        assert 40 < result["avg_processing_time"]["value"] < 56

    async def test_material_cost(self, async_session):
        """Should compute cost from formulation JSON and material master."""
        async_session.add(SolidificationMaterial(
            id=uuid.uuid4(),
            name="普通ポルトランドセメント",
            material_type="cement",
            unit_cost=15.0,
            is_active=True,
        ))
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="工場A",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="formulated",
            formulation={
                "solidifierType": "普通ポルトランドセメント",
                "solidifierAmount": 100,
                "suppressorType": None,
                "suppressorAmount": 0,
            },
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        # 100 kg * 15 JPY/kg = 1500 JPY
        assert result["material_cost"]["value"] == 1500.0

    async def test_material_cost_default(self, async_session):
        """Should use default costs when material not in master."""
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="工場B",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="formulated",
            formulation={
                "solidifierType": "未登録セメント",
                "solidifierAmount": 100,
                "suppressorType": "キレート剤X",
                "suppressorAmount": 5,
            },
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        # 100 * 15(default) + 5 * 50(default) = 1500 + 250 = 1750
        assert result["material_cost"]["value"] == 1750.0

    async def test_trend_calculation(self, async_session):
        """Should calculate trend from previous period comparison."""
        now = datetime.utcnow()
        # Current period: 2 records
        for i in range(2):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"current_{i}",
                delivery_date=now - timedelta(days=1),
                waste_type="汚泥",
                status="pending",
            ))
        # Previous period: 4 records
        for i in range(4):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"prev_{i}",
                delivery_date=now - timedelta(days=10),
                waste_type="汚泥",
                status="pending",
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_realtime(days=7)
        assert result["processing_volume"]["value"] == 2
        assert result["processing_volume"]["trend"] == -50.0


@pytest.mark.asyncio
class TestKPITrends:
    """Tests for KPIService.get_trends()."""

    async def test_empty_db(self, async_session):
        """Should return zero-valued data for all months."""
        service = KPIService(async_session)
        result = await service.get_trends(months=3)
        assert result["months"] == 3
        assert len(result["data"]) == 3
        assert all(p["processing_volume"] == 0 for p in result["data"])

    async def test_with_data(self, async_session):
        """Should include records in the correct month."""
        now = datetime.utcnow()
        mid_month = now.replace(day=15, hour=12, minute=0, second=0, microsecond=0)
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="工場A",
            delivery_date=mid_month,
            waste_type="汚泥",
            status="formulated",
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_trends(months=1)
        current_period = mid_month.strftime("%Y-%m")
        matching = [p for p in result["data"] if p["period"] == current_period]
        assert len(matching) == 1
        assert matching[0]["processing_volume"] == 1
        assert matching[0]["success_rate"] == 100.0


@pytest.mark.asyncio
class TestKPIAlerts:
    """Tests for KPIService.get_alerts()."""

    async def test_no_alerts(self, async_session):
        """Should return empty list when no issues."""
        service = KPIService(async_session)
        result = await service.get_alerts(days=7)
        assert result["total"] == 0
        assert result["alerts"] == []

    async def test_elution_violation_alert(self, async_session):
        """Should create critical alerts for elution violations."""
        async_session.add(WasteRecord(
            id=uuid.uuid4(),
            source="NG工場",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="tested",
            elution_result={"Pb": 0.05, "As": 0.02},
        ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_alerts(days=7)
        assert result["total"] >= 2  # Pb + As violations
        assert any(a["metric"] == "Pb" for a in result["alerts"])
        assert any(a["metric"] == "As" for a in result["alerts"])
        assert all(a["severity"] == "critical" for a in result["alerts"]
                    if a["metric"] in ("Pb", "As"))

    async def test_low_success_rate_alert(self, async_session):
        """Should warn when success rate is below threshold."""
        for i, status in enumerate(["pending", "pending", "pending", "formulated"]):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=6),
                waste_type="汚泥",
                status=status,
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_alerts(days=7)
        success_alerts = [a for a in result["alerts"] if a["metric"] == "formulation_success_rate"]
        assert len(success_alerts) == 1
        assert success_alerts[0]["severity"] == "warning"

    async def test_low_ml_usage_alert(self, async_session):
        """Should warn when ML usage is below threshold."""
        # 10 waste records, 0 ml_predictions → 0% ML usage
        for i in range(10):
            async_session.add(WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=6),
                waste_type="汚泥",
                status="formulated",
            ))
        await async_session.commit()

        service = KPIService(async_session)
        result = await service.get_alerts(days=7)
        ml_alerts = [a for a in result["alerts"] if a["metric"] == "ml_usage_rate"]
        assert len(ml_alerts) == 1
        assert ml_alerts[0]["severity"] == "warning"
