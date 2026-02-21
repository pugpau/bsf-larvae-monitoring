"""Workflow service orchestrating delivery → formulation → verification pipeline.

Integrates:
- FormulationPredictor (ML → similarity → rule fallback)
- FormulationOptimizer (PuLP LP cost minimization)
- FormulationRecordRepository (CRUD + status transitions)
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    Recipe,
    RecipeDetail,
    SolidificationMaterial,
    LeachingSuppressant,
    WasteRecord,
)
from src.activity.service import ActivityService
from src.formulation.repository import FormulationRecordRepository
from src.ml.predictor import FormulationPredictor
from src.ml.schemas import OptimizationRequest
from src.optimization.solver import FormulationOptimizer
from src.waste.repository import WasteRepository

logger = logging.getLogger(__name__)


class FormulationWorkflowService:
    """Orchestrates the formulation workflow from recommendation to verification."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FormulationRecordRepository(session)
        self.waste_repo = WasteRepository(session)
        self.predictor = FormulationPredictor(session)
        self._activity = ActivityService(session)

    async def recommend(
        self,
        waste_record_id: str,
        top_k: int = 3,
        created_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate formulation candidates for a waste record.

        Calls predictor (ML/similarity/rule), optimizer, and matching recipes.
        Creates FormulationRecord entries for each candidate (status=proposed).

        Returns list of created formulation records.
        """
        waste = await self.waste_repo.get_by_id(waste_record_id)
        if not waste:
            raise ValueError(f"WasteRecord {waste_record_id} not found")

        analysis = waste.get("analysis") or {}
        waste_type = waste.get("wasteType", "")
        if not analysis:
            raise ValueError("WasteRecord has no analysis data. Run analysis first.")

        candidates: List[Dict[str, Any]] = []

        # 1) ML/similarity/rule prediction
        try:
            history = await self._get_history(waste_type)
            prediction = await self.predictor.predict(
                analysis=analysis,
                waste_type=waste_type,
                history=history,
                waste_record_id=waste_record_id,
            )
            if prediction and prediction.get("recommendation"):
                record = await self.repo.create({
                    "waste_record_id": uuid.UUID(waste_record_id),
                    "source_type": prediction.get("method", "rule"),
                    "planned_formulation": prediction["recommendation"],
                    "confidence": prediction.get("confidence"),
                    "reasoning": prediction.get("reasoning", []),
                    "created_by": uuid.UUID(created_by) if created_by else None,
                })
                if record:
                    candidates.append(record)
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")

        # 2) Optimization (if we have material DB data)
        try:
            opt_result = await self._run_optimization(analysis, waste_type)
            if opt_result and opt_result.get("status") == "optimal":
                record = await self.repo.create({
                    "waste_record_id": uuid.UUID(waste_record_id),
                    "source_type": "optimization",
                    "planned_formulation": opt_result.get("formulation", {}),
                    "estimated_cost": opt_result.get("total_cost"),
                    "confidence": 0.7,
                    "reasoning": opt_result.get("reasoning", ["PuLP最適化結果"]),
                    "created_by": uuid.UUID(created_by) if created_by else None,
                })
                if record:
                    candidates.append(record)
        except Exception as e:
            logger.warning(f"Optimization failed: {e}")

        # 3) Matching active recipes
        try:
            recipe_candidates = await self._find_matching_recipes(waste_type, top_k)
            for rc in recipe_candidates:
                record = await self.repo.create({
                    "waste_record_id": uuid.UUID(waste_record_id),
                    "recipe_id": uuid.UUID(rc["recipe_id"]),
                    "recipe_version": rc.get("version"),
                    "source_type": "recipe",
                    "planned_formulation": rc.get("formulation"),
                    "confidence": 0.6,
                    "reasoning": [f"既存レシピ「{rc.get('name', '')}」に基づく配合"],
                    "created_by": uuid.UUID(created_by) if created_by else None,
                })
                if record:
                    candidates.append(record)
        except Exception as e:
            logger.warning(f"Recipe matching failed: {e}")

        # Update waste record status to analyzed (if still pending)
        if waste.get("status") == "pending" and candidates:
            await self.waste_repo.update(waste_record_id, {"status": "analyzed"})

        # Log activity
        if candidates:
            await self._activity.log_formulation_event(
                action="recommend",
                formulation_id=waste_record_id,
                title=f"{len(candidates)}件の配合候補を生成",
                description=f"搬入元: {waste.get('source', '?')}, 種別: {waste_type}",
                user_id=created_by,
                metadata={"candidate_count": len(candidates), "waste_type": waste_type},
            )

        return candidates[:top_k]

    async def accept(self, formulation_id: str) -> Optional[Dict[str, Any]]:
        """Accept a proposed formulation candidate."""
        result = await self.repo.transition_status(formulation_id, "accepted")
        if result:
            await self._activity.log_formulation_event(
                action="accept",
                formulation_id=formulation_id,
                title="配合案を承認",
                metadata={"source_type": result.get("source_type")},
            )
        return result

    async def apply_formulation(
        self,
        formulation_id: str,
        actual_formulation: Optional[Dict[str, Any]] = None,
        actual_cost: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Apply formulation (accepted → applied). Updates WasteRecord.formulation."""
        record = await self.repo.get_by_id(formulation_id)
        if not record:
            return None

        extra: Dict[str, Any] = {}
        if actual_formulation:
            extra["actual_formulation"] = actual_formulation
        if actual_cost is not None:
            extra["actual_cost"] = actual_cost

        result = await self.repo.transition_status(formulation_id, "applied", extra)
        if not result:
            return None

        # Update WasteRecord with applied formulation
        formulation_data = actual_formulation or record.get("planned_formulation", {})
        await self.waste_repo.update(
            record["waste_record_id"],
            {"formulation": formulation_data, "status": "formulated"},
        )

        await self._activity.log_formulation_event(
            action="apply",
            formulation_id=formulation_id,
            title="配合を適用",
            description=f"実コスト: {actual_cost}円" if actual_cost else None,
            metadata={"actual_cost": actual_cost},
        )

        return result

    async def verify(
        self,
        formulation_id: str,
        elution_result: Dict[str, Any],
        elution_passed: bool,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Verify formulation with elution test results (applied → verified)."""
        record = await self.repo.get_by_id(formulation_id)
        if not record:
            return None

        extra: Dict[str, Any] = {
            "elution_result": elution_result,
            "elution_passed": elution_passed,
        }
        if notes:
            extra["notes"] = notes

        result = await self.repo.transition_status(formulation_id, "verified", extra)
        if not result:
            return None

        # Update WasteRecord with elution results
        waste_status = "completed" if elution_passed else "failed"
        await self.waste_repo.update(
            record["waste_record_id"],
            {
                "elutionResult": elution_result,
                "status": waste_status,
            },
        )

        severity = "info" if elution_passed else "warning"
        title = "溶出試験合格" if elution_passed else "溶出試験不合格"
        await self._activity.log_formulation_event(
            action="verify",
            formulation_id=formulation_id,
            title=title,
            description=notes,
            severity=severity,
            metadata={"elution_passed": elution_passed},
        )

        return result

    async def reject(
        self, formulation_id: str, notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reject a formulation at any valid stage."""
        extra = {"notes": notes} if notes else None
        result = await self.repo.transition_status(formulation_id, "rejected", extra)
        if result:
            await self._activity.log_formulation_event(
                action="reject",
                formulation_id=formulation_id,
                title="配合案を却下",
                description=notes,
                severity="warning",
            )
        return result

    # ── Private helpers ──

    async def _get_history(self, waste_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent waste records of same type for similarity matching."""
        result = await self.session.execute(
            select(WasteRecord)
            .where(WasteRecord.waste_type == waste_type)
            .where(WasteRecord.formulation.isnot(None))
            .order_by(WasteRecord.created_at.desc())
            .limit(limit)
        )
        records = result.scalars().all()
        history = []
        for r in records:
            history.append({
                "analysis": r.analysis or {},
                "formulation": r.formulation or {},
                "elutionResult": r.elution_result,
                "wasteType": r.waste_type,
            })
        return history

    async def _run_optimization(
        self,
        analysis: Dict[str, Any],
        waste_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Run PuLP optimization with available materials."""
        # Fetch available solidifiers
        sol_result = await self.session.execute(
            select(SolidificationMaterial)
            .where(SolidificationMaterial.is_active == True)  # noqa: E712
        )
        solidifiers = [
            {
                "name": s.name,
                "material_type": s.material_type,
                "min_rate": s.min_addition_rate or 0,
                "max_rate": s.max_addition_rate or 500,
                "unit_cost": s.unit_cost or 15.0,
            }
            for s in sol_result.scalars().all()
        ]

        # Fetch available suppressants
        sup_result = await self.session.execute(
            select(LeachingSuppressant)
            .where(LeachingSuppressant.is_active == True)  # noqa: E712
        )
        suppressants = [
            {
                "name": s.name,
                "min_rate": s.min_addition_rate or 0,
                "max_rate": s.max_addition_rate or 100,
                "unit_cost": s.unit_cost or 50.0,
            }
            for s in sup_result.scalars().all()
        ]

        if not solidifiers:
            return None

        request = OptimizationRequest(
            analysis=analysis,
            waste_type=waste_type,
            weight=1.0,
        )

        optimizer = FormulationOptimizer()
        result = optimizer.optimize(request, solidifiers, suppressants)

        return {
            "status": result.status,
            "total_cost": result.total_cost,
            "formulation": result.formulation,
            "reasoning": result.reasoning,
        }

    async def _find_matching_recipes(
        self,
        waste_type: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find active recipes matching the waste type."""
        result = await self.session.execute(
            select(Recipe)
            .where(Recipe.waste_type == waste_type)
            .where(Recipe.status == "active")
            .limit(top_k)
        )
        recipes = result.scalars().all()

        recipe_candidates = []
        for recipe in recipes:
            # Fetch recipe details
            det_result = await self.session.execute(
                select(RecipeDetail)
                .where(RecipeDetail.recipe_id == recipe.id)
                .order_by(RecipeDetail.order_index)
            )
            details = det_result.scalars().all()

            formulation: Dict[str, Any] = {"details": []}
            for d in details:
                formulation["details"].append({
                    "material_id": str(d.material_id),
                    "material_type": d.material_type,
                    "addition_rate": d.addition_rate,
                    "order_index": d.order_index,
                })
                # Map first solidifier/suppressant for compatibility
                if d.material_type == "solidification" and "solidifierAmount" not in formulation:
                    formulation["solidifierAmount"] = d.addition_rate
                    formulation["solidifierUnit"] = "kg/t"
                elif d.material_type == "suppressant" and "suppressorAmount" not in formulation:
                    formulation["suppressorAmount"] = d.addition_rate
                    formulation["suppressorUnit"] = "kg/t"

            recipe_candidates.append({
                "recipe_id": str(recipe.id),
                "name": recipe.name,
                "version": recipe.current_version,
                "formulation": formulation,
            })

        return recipe_candidates
