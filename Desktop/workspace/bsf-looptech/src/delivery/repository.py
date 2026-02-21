"""Repositories for incoming materials and delivery schedules."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgresql import (
    DeliverySchedule,
    IncomingMaterial,
    Supplier,
)
from src.materials.repository import _BaseRepository

logger = logging.getLogger(__name__)


class IncomingMaterialRepository(_BaseRepository):
    """Repository for IncomingMaterial CRUD with supplier join."""

    _search_columns = ["name", "material_category", "description"]
    _sortable_columns = [
        "name", "material_category", "is_active", "created_at", "updated_at",
    ]

    def __init__(self, session: AsyncSession):
        super().__init__(session, IncomingMaterial)

    def _to_dict_with_supplier(self, obj: IncomingMaterial) -> Dict[str, Any]:
        """Convert to dict with supplier_name from eagerly loaded relationship."""
        d = self._to_dict(obj)
        d["supplier_name"] = obj.supplier_rel.name if obj.supplier_rel else None
        return d

    async def get_all(
        self,
        q: Optional[str] = None,
        supplier_id: Optional[str] = None,
        material_category: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
        **filters: Any,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all with search across incoming_materials + supplier name."""
        stmt = select(IncomingMaterial).options(
            selectinload(IncomingMaterial.supplier_rel)
        )
        count_stmt = select(func.count()).select_from(IncomingMaterial)

        # Exact-match filters
        if supplier_id is not None:
            uid = uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id
            stmt = stmt.where(IncomingMaterial.supplier_id == uid)
            count_stmt = count_stmt.where(IncomingMaterial.supplier_id == uid)
        if material_category is not None:
            stmt = stmt.where(IncomingMaterial.material_category == material_category)
            count_stmt = count_stmt.where(IncomingMaterial.material_category == material_category)
        if is_active is not None:
            stmt = stmt.where(IncomingMaterial.is_active == is_active)
            count_stmt = count_stmt.where(IncomingMaterial.is_active == is_active)

        # Text search: incoming_materials columns + supplier.name via JOIN
        if q:
            pattern = f"%{q}%"
            conditions = [
                IncomingMaterial.name.ilike(pattern),
                IncomingMaterial.material_category.ilike(pattern),
                IncomingMaterial.description.ilike(pattern),
            ]
            # JOIN supplier for name search
            supplier_subq = (
                select(Supplier.id)
                .where(Supplier.name.ilike(pattern))
                .correlate(None)
            )
            conditions.append(IncomingMaterial.supplier_id.in_(supplier_subq))
            search_filter = or_(*conditions)
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Count
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        sort_col = None
        if sort_by and sort_by in self._sortable_columns and hasattr(IncomingMaterial, sort_by):
            sort_col = getattr(IncomingMaterial, sort_by)
        if sort_col is None:
            sort_col = IncomingMaterial.created_at
        stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        items = [self._to_dict_with_supplier(obj) for obj in result.scalars().all()]
        return items, total

    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(IncomingMaterial)
            .options(selectinload(IncomingMaterial.supplier_rel))
            .where(IncomingMaterial.id == uid)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        return self._to_dict_with_supplier(obj)

    async def get_categories_by_supplier(self, supplier_id: str) -> List[str]:
        """Return distinct material_category values for a supplier (active only)."""
        uid = uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id
        stmt = (
            select(IncomingMaterial.material_category)
            .where(IncomingMaterial.supplier_id == uid, IncomingMaterial.is_active == True)  # noqa: E712
            .distinct()
            .order_by(IncomingMaterial.material_category)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_by_supplier_and_category(
        self,
        supplier_id: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return active materials for a supplier, optionally filtered by category."""
        uid = uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id
        stmt = select(IncomingMaterial).where(
            IncomingMaterial.supplier_id == uid,
            IncomingMaterial.is_active == True,  # noqa: E712
        )
        if category:
            stmt = stmt.where(IncomingMaterial.material_category == category)
        stmt = stmt.order_by(IncomingMaterial.name)
        result = await self.session.execute(stmt)
        return [self._to_dict(m) for m in result.scalars().all()]


class DeliveryScheduleRepository:
    """Repository for DeliverySchedule CRUD with joined fields."""

    _sortable_columns = {
        "scheduled_date", "status", "estimated_weight", "actual_weight",
        "created_at", "updated_at",
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            record = DeliverySchedule(
                id=uuid.uuid4(),
                incoming_material_id=data["incoming_material_id"],
                scheduled_date=datetime.fromisoformat(data["scheduled_date"]),
                estimated_weight=data.get("estimated_weight"),
                weight_unit=data.get("weight_unit", "t"),
                notes=data.get("notes"),
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
            return await self.get_by_id(str(record.id))
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create delivery schedule: {e}")
            return None

    async def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(DeliverySchedule)
            .options(
                selectinload(DeliverySchedule.incoming_material_rel)
                .selectinload(IncomingMaterial.supplier_rel)
            )
            .where(DeliverySchedule.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._to_dict_with_joins(record)

    async def get_all(
        self,
        q: Optional[str] = None,
        status: Optional[str] = None,
        incoming_material_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        stmt = select(DeliverySchedule).options(
            selectinload(DeliverySchedule.incoming_material_rel)
            .selectinload(IncomingMaterial.supplier_rel)
        )
        count_stmt = select(func.count()).select_from(DeliverySchedule)

        if status:
            stmt = stmt.where(DeliverySchedule.status == status)
            count_stmt = count_stmt.where(DeliverySchedule.status == status)
        if incoming_material_id:
            uid = uuid.UUID(incoming_material_id)
            stmt = stmt.where(DeliverySchedule.incoming_material_id == uid)
            count_stmt = count_stmt.where(DeliverySchedule.incoming_material_id == uid)
        if date_from:
            d = datetime.fromisoformat(date_from)
            stmt = stmt.where(DeliverySchedule.scheduled_date >= d)
            count_stmt = count_stmt.where(DeliverySchedule.scheduled_date >= d)
        if date_to:
            from datetime import timedelta
            d = datetime.fromisoformat(date_to) + timedelta(days=1)
            stmt = stmt.where(DeliverySchedule.scheduled_date < d)
            count_stmt = count_stmt.where(DeliverySchedule.scheduled_date < d)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(DeliverySchedule.notes.ilike(pattern))
            count_stmt = count_stmt.where(DeliverySchedule.notes.ilike(pattern))

        # Count
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sort
        if sort_by and sort_by in self._sortable_columns:
            col = getattr(DeliverySchedule, sort_by, None)
            if col is not None:
                stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        else:
            stmt = stmt.order_by(DeliverySchedule.scheduled_date.desc())

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        items = [self._to_dict_with_joins(record) for record in records]
        return items, total

    async def update(self, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(DeliverySchedule).where(DeliverySchedule.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        _UPDATABLE_FIELDS = {
            "incoming_material_id", "scheduled_date", "estimated_weight",
            "actual_weight", "weight_unit", "notes",
        }
        for key, value in data.items():
            if key not in _UPDATABLE_FIELDS:
                continue
            if key == "scheduled_date" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            if key == "incoming_material_id" and isinstance(value, str):
                value = uuid.UUID(value)
            setattr(record, key, value)

        await self.session.commit()
        await self.session.refresh(record)
        return await self.get_by_id(str(record.id))

    async def delete(self, item_id: str) -> bool:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(DeliverySchedule).where(DeliverySchedule.id == uid)
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def get_all_for_export(self, **filters: Any) -> List[Dict[str, Any]]:
        stmt = select(DeliverySchedule).options(
            selectinload(DeliverySchedule.incoming_material_rel)
            .selectinload(IncomingMaterial.supplier_rel)
        )
        if "status" in filters and filters["status"]:
            stmt = stmt.where(DeliverySchedule.status == filters["status"])
        stmt = stmt.order_by(DeliverySchedule.scheduled_date.desc()).limit(50000)
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [self._to_dict_with_joins(record) for record in records]

    def _to_dict_with_joins(self, record: DeliverySchedule) -> Dict[str, Any]:
        """Convert to dict with supplier_name, material_category, material_name.

        Relies on eagerly loaded relationships (selectinload) — no DB queries.
        """
        supplier_name = None
        material_category = None
        material_name = None

        mat = record.incoming_material_rel
        if mat:
            material_category = mat.material_category
            material_name = mat.name
            if mat.supplier_rel:
                supplier_name = mat.supplier_rel.name

        return {
            "id": str(record.id),
            "incoming_material_id": str(record.incoming_material_id),
            "supplier_name": supplier_name,
            "material_category": material_category,
            "material_name": material_name,
            "scheduled_date": record.scheduled_date.strftime("%Y-%m-%d") if record.scheduled_date else None,
            "estimated_weight": record.estimated_weight,
            "actual_weight": record.actual_weight,
            "weight_unit": record.weight_unit,
            "status": record.status,
            "waste_record_id": str(record.waste_record_id) if record.waste_record_id else None,
            "notes": record.notes,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
