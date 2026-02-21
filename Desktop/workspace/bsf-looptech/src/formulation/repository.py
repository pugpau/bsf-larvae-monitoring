"""Repository layer for formulation records."""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    FormulationRecord,
    Recipe,
    WasteRecord,
)

logger = logging.getLogger(__name__)

# Valid status transitions
VALID_TRANSITIONS: Dict[str, set] = {
    "proposed": {"accepted", "rejected"},
    "accepted": {"applied", "rejected"},
    "applied": {"verified", "rejected"},
}


class FormulationRecordRepository:
    """CRUD + status transition for formulation records."""

    _sortable_columns = {
        "created_at", "updated_at", "status", "source_type",
        "confidence", "estimated_cost",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = FormulationRecord(
            id=uuid.uuid4(),
            waste_record_id=data["waste_record_id"],
            recipe_id=data.get("recipe_id"),
            recipe_version=data.get("recipe_version"),
            prediction_id=data.get("prediction_id"),
            source_type=data.get("source_type", "manual"),
            status="proposed",
            planned_formulation=data.get("planned_formulation"),
            estimated_cost=data.get("estimated_cost"),
            confidence=data.get("confidence"),
            reasoning=data.get("reasoning"),
            notes=data.get("notes"),
            created_by=data.get("created_by"),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return await self.get_by_id(str(record.id))  # type: ignore[return-value]

    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(FormulationRecord).where(FormulationRecord.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        return await self._to_dict_enriched(record)

    async def get_all(
        self,
        waste_record_id: Optional[str] = None,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        stmt = select(FormulationRecord)
        count_stmt = select(func.count()).select_from(FormulationRecord)

        if waste_record_id:
            uid = uuid.UUID(waste_record_id)
            stmt = stmt.where(FormulationRecord.waste_record_id == uid)
            count_stmt = count_stmt.where(FormulationRecord.waste_record_id == uid)
        if status:
            stmt = stmt.where(FormulationRecord.status == status)
            count_stmt = count_stmt.where(FormulationRecord.status == status)
        if source_type:
            stmt = stmt.where(FormulationRecord.source_type == source_type)
            count_stmt = count_stmt.where(FormulationRecord.source_type == source_type)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sort
        if sort_by and sort_by in self._sortable_columns:
            col = getattr(FormulationRecord, sort_by, None)
            if col is not None:
                stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        else:
            stmt = stmt.order_by(FormulationRecord.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        records = result.scalars().all()
        items = []
        for record in records:
            items.append(await self._to_dict_enriched(record))
        return items, total

    async def get_by_waste_record(self, waste_record_id: str) -> List[Dict[str, Any]]:
        """Get all formulation records for a waste record, ordered by created_at desc."""
        uid = uuid.UUID(waste_record_id) if isinstance(waste_record_id, str) else waste_record_id
        result = await self.session.execute(
            select(FormulationRecord)
            .where(FormulationRecord.waste_record_id == uid)
            .order_by(FormulationRecord.created_at.desc())
            .limit(50)
        )
        records = result.scalars().all()
        items = []
        for record in records:
            items.append(await self._to_dict_enriched(record))
        return items

    async def update(self, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(FormulationRecord).where(FormulationRecord.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        updatable = {
            "recipe_id", "recipe_version", "planned_formulation",
            "actual_formulation", "estimated_cost", "actual_cost", "notes",
        }
        for key, value in data.items():
            if key in updatable:
                if key in ("recipe_id",) and isinstance(value, str):
                    value = uuid.UUID(value)
                setattr(record, key, value)

        await self.session.commit()
        await self.session.refresh(record)
        return await self.get_by_id(str(record.id))

    async def transition_status(
        self,
        item_id: str,
        new_status: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Transition formulation record status with validation.

        proposed → accepted/rejected
        accepted → applied/rejected
        applied → verified/rejected
        """
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(FormulationRecord).where(FormulationRecord.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        old_status = record.status
        allowed = VALID_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{old_status}' to '{new_status}'. "
                f"Allowed: {allowed or 'none (terminal state)'}"
            )

        record.status = new_status

        if extra_data:
            if "actual_formulation" in extra_data:
                record.actual_formulation = extra_data["actual_formulation"]
            if "elution_result" in extra_data:
                record.elution_result = extra_data["elution_result"]
            if "elution_passed" in extra_data:
                record.elution_passed = extra_data["elution_passed"]
            if "actual_cost" in extra_data:
                record.actual_cost = extra_data["actual_cost"]
            if "notes" in extra_data:
                record.notes = extra_data["notes"]

        await self.session.commit()
        await self.session.refresh(record)
        return await self.get_by_id(str(record.id))

    async def delete(self, item_id: str) -> bool:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(FormulationRecord).where(FormulationRecord.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        if record.status not in ("proposed", "rejected"):
            raise ValueError(
                f"Cannot delete record with status '{record.status}'. "
                "Only 'proposed' or 'rejected' records can be deleted."
            )
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def _to_dict_enriched(self, record: FormulationRecord) -> Dict[str, Any]:
        """Convert to dict with joined waste_type, waste_source, recipe_name."""
        d = {
            "id": str(record.id),
            "waste_record_id": str(record.waste_record_id),
            "recipe_id": str(record.recipe_id) if record.recipe_id else None,
            "recipe_version": record.recipe_version,
            "prediction_id": str(record.prediction_id) if record.prediction_id else None,
            "source_type": record.source_type,
            "status": record.status,
            "planned_formulation": record.planned_formulation,
            "actual_formulation": record.actual_formulation,
            "elution_result": record.elution_result,
            "elution_passed": record.elution_passed,
            "estimated_cost": record.estimated_cost,
            "actual_cost": record.actual_cost,
            "confidence": record.confidence,
            "reasoning": record.reasoning,
            "notes": record.notes,
            "created_by": str(record.created_by) if record.created_by else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

        # Enrich with waste record info
        waste_result = await self.session.execute(
            select(WasteRecord.waste_type, WasteRecord.source)
            .where(WasteRecord.id == record.waste_record_id)
        )
        waste_row = waste_result.first()
        d["waste_type"] = waste_row[0] if waste_row else None
        d["waste_source"] = waste_row[1] if waste_row else None

        # Enrich with recipe name
        if record.recipe_id:
            recipe_result = await self.session.execute(
                select(Recipe.name).where(Recipe.id == record.recipe_id)
            )
            d["recipe_name"] = recipe_result.scalar_one_or_none()
        else:
            d["recipe_name"] = None

        return d
