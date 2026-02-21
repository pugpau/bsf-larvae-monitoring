"""KPI service — computes realtime metrics, trends, and alerts from existing tables."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    LeachingSuppressant,
    MLPrediction,
    SolidificationMaterial,
    WasteRecord,
)
from src.waste.service import ELUTION_THRESHOLDS

logger = logging.getLogger(__name__)

# Default costs (consistent with src/optimization/solver.py)
_DEFAULT_SOLIDIFIER_COST = 15.0  # JPY/kg
_DEFAULT_SUPPRESSANT_COST = 50.0  # JPY/kg

# Success statuses for formulation
_SUCCESS_STATUSES = ("formulated", "tested", "passed")

# Status thresholds
_VIOLATION_WARNING = 10.0  # %
_VIOLATION_CRITICAL = 20.0  # %
_SUCCESS_RATE_WARNING = 70.0  # %
_SUCCESS_RATE_CRITICAL = 50.0  # %
_ML_USAGE_WARNING = 20.0  # %
_PROCESSING_TIME_WARNING = 72.0  # hours


class KPIService:
    """Computes 6 KPI metrics from waste_records + ml_predictions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_realtime(self, days: int = 7) -> dict[str, Any]:
        """Compute all 6 KPIs for the given period with trend from previous period."""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        prev_start = period_start - timedelta(days=days)

        # Current period metrics
        cur = await self._compute_metrics(period_start, now)
        # Previous period metrics for trend calculation
        prev = await self._compute_metrics(prev_start, period_start)

        def _trend(cur_val: float, prev_val: float) -> Optional[float]:
            if prev_val == 0:
                return None
            return round((cur_val - prev_val) / prev_val * 100, 1)

        def _status_violation(rate: float) -> str:
            if rate >= _VIOLATION_CRITICAL:
                return "critical"
            if rate >= _VIOLATION_WARNING:
                return "warning"
            return "normal"

        def _status_success(rate: float) -> str:
            if rate < _SUCCESS_RATE_CRITICAL:
                return "critical"
            if rate < _SUCCESS_RATE_WARNING:
                return "warning"
            return "normal"

        def _status_ml(rate: float) -> str:
            if rate < _ML_USAGE_WARNING:
                return "warning"
            return "normal"

        def _status_time(hours: float) -> str:
            if hours > _PROCESSING_TIME_WARNING:
                return "warning"
            return "normal"

        return {
            "period_days": days,
            "processing_volume": {
                "label": "処理量",
                "value": cur["volume"],
                "unit": "件",
                "trend": _trend(cur["volume"], prev["volume"]),
                "status": "normal",
            },
            "formulation_success_rate": {
                "label": "配合成功率",
                "value": cur["success_rate"],
                "unit": "%",
                "trend": _trend(cur["success_rate"], prev["success_rate"]),
                "status": _status_success(cur["success_rate"]),
            },
            "material_cost": {
                "label": "材料コスト",
                "value": cur["material_cost"],
                "unit": "円",
                "trend": _trend(cur["material_cost"], prev["material_cost"]),
                "status": "normal",
            },
            "ml_usage_rate": {
                "label": "ML予測利用率",
                "value": cur["ml_usage_rate"],
                "unit": "%",
                "trend": _trend(cur["ml_usage_rate"], prev["ml_usage_rate"]),
                "status": _status_ml(cur["ml_usage_rate"]),
            },
            "avg_processing_time": {
                "label": "平均処理時間",
                "value": cur["avg_processing_time"],
                "unit": "時間",
                "trend": _trend(cur["avg_processing_time"], prev["avg_processing_time"]),
                "status": _status_time(cur["avg_processing_time"]),
            },
            "violation_rate": {
                "label": "基準値逸脱率",
                "value": cur["violation_rate"],
                "unit": "%",
                "trend": _trend(cur["violation_rate"], prev["violation_rate"]),
                "status": _status_violation(cur["violation_rate"]),
            },
            "updated_at": now.isoformat(),
        }

    async def get_trends(self, months: int = 6) -> dict[str, Any]:
        """Compute monthly KPI trends."""
        now = datetime.now(timezone.utc)
        data = []

        for i in range(months - 1, -1, -1):
            # Calculate month boundaries
            ref = now - timedelta(days=i * 30)
            month_start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)

            metrics = await self._compute_metrics(month_start, month_end)
            data.append({
                "period": month_start.strftime("%Y-%m"),
                "processing_volume": metrics["volume"],
                "success_rate": metrics["success_rate"],
                "material_cost": metrics["material_cost"],
                "ml_usage_rate": metrics["ml_usage_rate"],
                "avg_processing_time_hours": metrics["avg_processing_time"],
                "violation_rate": metrics["violation_rate"],
            })

        return {"months": months, "data": data}

    async def get_alerts(self, days: int = 7) -> dict[str, Any]:
        """Get active KPI alerts — elution violations and metric warnings."""
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        alerts: list[dict] = []

        # Elution violations
        stmt = select(WasteRecord).where(
            WasteRecord.delivery_date >= period_start,
            WasteRecord.elution_result.isnot(None),
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        for record in records:
            elution = record.elution_result
            if not isinstance(elution, dict):
                continue
            for metal, threshold in ELUTION_THRESHOLDS.items():
                value = elution.get(metal)
                if value is not None and value > threshold:
                    alerts.append({
                        "severity": "critical",
                        "metric": metal,
                        "message": f"{record.source}: {metal} = {value} (基準値 {threshold} 超過)",
                        "value": value,
                        "threshold": threshold,
                        "record_id": str(record.id),
                        "created_at": (record.delivery_date or now).isoformat(),
                    })

        # Metric-level warnings
        metrics = await self._compute_metrics(period_start, now)

        if metrics["volume"] > 0 and metrics["success_rate"] < _SUCCESS_RATE_CRITICAL:
            alerts.append({
                "severity": "warning",
                "metric": "formulation_success_rate",
                "message": f"配合成功率が低下しています: {metrics['success_rate']:.1f}%",
                "value": metrics["success_rate"],
                "threshold": _SUCCESS_RATE_CRITICAL,
                "created_at": now.isoformat(),
            })

        if metrics["volume"] > 0 and metrics["ml_usage_rate"] < _ML_USAGE_WARNING:
            alerts.append({
                "severity": "warning",
                "metric": "ml_usage_rate",
                "message": f"ML予測利用率が低下しています: {metrics['ml_usage_rate']:.1f}%",
                "value": metrics["ml_usage_rate"],
                "threshold": _ML_USAGE_WARNING,
                "created_at": now.isoformat(),
            })

        # Sort: critical first, then by created_at desc
        alerts.sort(key=lambda a: (0 if a["severity"] == "critical" else 1, a["created_at"]), reverse=False)

        return {"alerts": alerts, "total": len(alerts)}

    # ── Private helpers ──

    async def _compute_metrics(
        self, start: datetime, end: datetime
    ) -> dict[str, float]:
        """Compute all 6 raw metric values for a date range."""
        s = self._session

        # KPI 1: Processing volume
        volume_result = await s.execute(
            select(func.count(WasteRecord.id)).where(
                WasteRecord.delivery_date >= start,
                WasteRecord.delivery_date < end,
            )
        )
        volume = volume_result.scalar() or 0

        # KPI 2: Formulation success rate
        success_result = await s.execute(
            select(func.count(WasteRecord.id)).where(
                WasteRecord.delivery_date >= start,
                WasteRecord.delivery_date < end,
                WasteRecord.status.in_(_SUCCESS_STATUSES),
            )
        )
        success_count = success_result.scalar() or 0
        success_rate = round(success_count / volume * 100, 1) if volume > 0 else 0.0

        # KPI 3: Material cost (computed in Python from formulation JSON)
        material_cost = await self._compute_material_cost(start, end)

        # KPI 4: ML usage rate
        ml_count_result = await s.execute(
            select(func.count(MLPrediction.id)).where(
                MLPrediction.created_at >= start,
                MLPrediction.created_at < end,
            )
        )
        ml_count = ml_count_result.scalar() or 0
        ml_usage_rate = round(ml_count / volume * 100, 1) if volume > 0 else 0.0

        # KPI 5: Average processing time (hours)
        avg_time = await self._compute_avg_processing_time(start, end)

        # KPI 6: Violation rate
        violation_rate = await self._compute_violation_rate(start, end)

        return {
            "volume": volume,
            "success_rate": success_rate,
            "material_cost": material_cost,
            "ml_usage_rate": ml_usage_rate,
            "avg_processing_time": avg_time,
            "violation_rate": violation_rate,
        }

    async def _compute_material_cost(self, start: datetime, end: datetime) -> float:
        """Compute total material cost from formulation JSON + material master."""
        cost_map = await self._get_material_cost_map()

        stmt = select(WasteRecord).where(
            WasteRecord.delivery_date >= start,
            WasteRecord.delivery_date < end,
            WasteRecord.formulation.isnot(None),
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        total_cost = 0.0
        for record in records:
            total_cost += self._compute_record_cost(record.formulation, cost_map)

        return round(total_cost, 1)

    async def _get_material_cost_map(self) -> dict[str, float]:
        """Build name → unit_cost mapping from material master tables."""
        cost_map: dict[str, float] = {}

        sol_result = await self._session.execute(
            select(SolidificationMaterial.name, SolidificationMaterial.unit_cost)
        )
        for name, cost in sol_result.all():
            if cost is not None:
                cost_map[name] = cost

        sup_result = await self._session.execute(
            select(LeachingSuppressant.name, LeachingSuppressant.unit_cost)
        )
        for name, cost in sup_result.all():
            if cost is not None:
                cost_map[name] = cost

        return cost_map

    @staticmethod
    def _compute_record_cost(
        formulation: Any, cost_map: dict[str, float]
    ) -> float:
        """Compute cost for a single record from its formulation JSON."""
        if not isinstance(formulation, dict):
            return 0.0

        cost = 0.0
        sol_type = formulation.get("solidifierType")
        sol_amount = formulation.get("solidifierAmount") or 0
        if sol_type and sol_amount:
            unit_cost = cost_map.get(sol_type, _DEFAULT_SOLIDIFIER_COST)
            cost += sol_amount * unit_cost

        sup_type = formulation.get("suppressorType")
        sup_amount = formulation.get("suppressorAmount") or 0
        if sup_type and sup_amount:
            unit_cost = cost_map.get(sup_type, _DEFAULT_SUPPRESSANT_COST)
            cost += sup_amount * unit_cost

        return cost

    async def _compute_avg_processing_time(
        self, start: datetime, end: datetime
    ) -> float:
        """Average hours from delivery_date to updated_at for completed records."""
        stmt = select(WasteRecord.delivery_date, WasteRecord.updated_at).where(
            WasteRecord.delivery_date >= start,
            WasteRecord.delivery_date < end,
            WasteRecord.status.in_(_SUCCESS_STATUSES),
            WasteRecord.updated_at.isnot(None),
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        if not rows:
            return 0.0

        total_hours = 0.0
        count = 0
        for delivery, updated in rows:
            if delivery and updated:
                delta = updated - delivery
                total_hours += delta.total_seconds() / 3600
                count += 1

        return round(total_hours / count, 1) if count > 0 else 0.0

    async def _compute_violation_rate(
        self, start: datetime, end: datetime
    ) -> float:
        """Percentage of elution-tested records that exceed thresholds."""
        stmt = select(WasteRecord).where(
            WasteRecord.delivery_date >= start,
            WasteRecord.delivery_date < end,
            WasteRecord.elution_result.isnot(None),
        )
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return 0.0

        violation_count = 0
        for record in records:
            elution = record.elution_result
            if not isinstance(elution, dict):
                continue
            for metal, threshold in ELUTION_THRESHOLDS.items():
                value = elution.get(metal)
                if value is not None and value > threshold:
                    violation_count += 1
                    break  # Count record once

        return round(violation_count / len(records) * 100, 1)
