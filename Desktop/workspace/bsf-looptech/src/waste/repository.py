"""
Repository for waste treatment records and material types.
Handles all database operations via SQLAlchemy async sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.database.postgresql import WasteRecord, MaterialType

logger = logging.getLogger(__name__)


class WasteRepository:
    """Repository for WasteRecord CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new waste record."""
        try:
            record = WasteRecord(
                source=data["source"],
                delivery_date=datetime.fromisoformat(data["deliveryDate"]),
                waste_type=data["wasteType"],
                weight=data.get("weight"),
                weight_unit=data.get("weightUnit", "t"),
                status=data.get("status", "pending"),
                analysis=data.get("analysis"),
                formulation=data.get("formulation"),
                elution_result=data.get("elutionResult"),
                notes=data.get("notes"),
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
            return self._to_dict(record)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create waste record: {e}")
            return None

    _sortable_columns = {"delivery_date", "source", "waste_type", "status", "weight", "created_at", "updated_at"}

    async def get_all(
        self,
        q: Optional[str] = None,
        status: Optional[str] = None,
        waste_type: Optional[str] = None,
        source: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 200,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get waste records with search, filters, pagination, sorting.

        Returns (items, total_count).
        """
        try:
            stmt = select(WasteRecord)
            count_stmt = select(func.count()).select_from(WasteRecord)

            # Exact-match filters
            if status:
                stmt = stmt.where(WasteRecord.status == status)
                count_stmt = count_stmt.where(WasteRecord.status == status)
            if waste_type:
                stmt = stmt.where(WasteRecord.waste_type == waste_type)
                count_stmt = count_stmt.where(WasteRecord.waste_type == waste_type)
            if source:
                stmt = stmt.where(WasteRecord.source == source)
                count_stmt = count_stmt.where(WasteRecord.source == source)

            # Text search (ILIKE on source, waste_type, notes)
            if q:
                pattern = f"%{q}%"
                search_filter = or_(
                    WasteRecord.source.ilike(pattern),
                    WasteRecord.waste_type.ilike(pattern),
                    WasteRecord.notes.ilike(pattern),
                )
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)

            # Total count (before pagination)
            total_result = await self.session.execute(count_stmt)
            total = total_result.scalar() or 0

            # Sorting (allowlist for security)
            sort_col = None
            if sort_by and sort_by in self._sortable_columns and hasattr(WasteRecord, sort_by):
                sort_col = getattr(WasteRecord, sort_by)
            if sort_col is None:
                sort_col = WasteRecord.delivery_date
            stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

            # Pagination
            stmt = stmt.offset(offset).limit(limit)

            result = await self.session.execute(stmt)
            records = result.scalars().all()
            return [self._to_dict(r) for r in records], total
        except Exception as e:
            logger.error(f"Failed to get waste records: {e}")
            return [], 0

    async def get_all_for_export(
        self,
        status: Optional[str] = None,
        waste_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all waste records without pagination (for CSV export)."""
        try:
            stmt = select(WasteRecord).order_by(desc(WasteRecord.delivery_date))
            if status:
                stmt = stmt.where(WasteRecord.status == status)
            if waste_type:
                stmt = stmt.where(WasteRecord.waste_type == waste_type)
            if source:
                stmt = stmt.where(WasteRecord.source == source)
            stmt = stmt.limit(50000)
            result = await self.session.execute(stmt)
            return [self._to_dict(r) for r in result.scalars().all()]
        except Exception as e:
            logger.error(f"Failed to export waste records: {e}")
            return []

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a waste record by ID."""
        try:
            result = await self.session.execute(
                select(WasteRecord).where(WasteRecord.id == record_id)
            )
            record = result.scalar_one_or_none()
            return self._to_dict(record) if record else None
        except Exception as e:
            logger.error(f"Failed to get waste record {record_id}: {e}")
            return None

    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a waste record."""
        try:
            values = {}
            if "source" in data and data["source"] is not None:
                values["source"] = data["source"]
            if "deliveryDate" in data and data["deliveryDate"] is not None:
                values["delivery_date"] = datetime.fromisoformat(data["deliveryDate"])
            if "wasteType" in data and data["wasteType"] is not None:
                values["waste_type"] = data["wasteType"]
            if "weight" in data:
                values["weight"] = data["weight"]
            if "weightUnit" in data and data["weightUnit"] is not None:
                values["weight_unit"] = data["weightUnit"]
            if "status" in data and data["status"] is not None:
                values["status"] = data["status"]
            if "analysis" in data:
                values["analysis"] = data["analysis"]
            if "formulation" in data:
                values["formulation"] = data["formulation"]
            if "elutionResult" in data:
                values["elution_result"] = data["elutionResult"]
            if "notes" in data:
                values["notes"] = data["notes"]

            values["updated_at"] = datetime.now(timezone.utc)

            await self.session.execute(
                update(WasteRecord).where(WasteRecord.id == record_id).values(**values)
            )
            await self.session.commit()
            return await self.get_by_id(record_id)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update waste record {record_id}: {e}")
            return None

    async def delete(self, record_id: str) -> bool:
        """Delete a waste record."""
        try:
            result = await self.session.execute(
                delete(WasteRecord).where(WasteRecord.id == record_id)
            )
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete waste record {record_id}: {e}")
            return False

    def _to_dict(self, record: WasteRecord) -> Dict[str, Any]:
        """Convert SQLAlchemy model to frontend-compatible dict."""
        return {
            "id": str(record.id),
            "source": record.source,
            "deliveryDate": record.delivery_date.strftime("%Y-%m-%d") if record.delivery_date else None,
            "wasteType": record.waste_type,
            "weight": record.weight,
            "weightUnit": record.weight_unit,
            "status": record.status,
            "analysis": record.analysis or {},
            "formulation": record.formulation,
            "elutionResult": record.elution_result,
            "notes": record.notes,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }


class MaterialTypeRepository:
    """Repository for MaterialType CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new material type."""
        try:
            record = MaterialType(
                name=data["name"],
                category=data["category"],
                description=data.get("description"),
                supplier=data.get("supplier"),
                unit_cost=data.get("unitCost"),
                unit=data.get("unit"),
                attributes=data.get("attributes"),
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
            return self._to_dict(record)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create material type: {e}")
            return None

    async def get_all(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all material types with optional category filter."""
        try:
            query = select(MaterialType).order_by(MaterialType.category, MaterialType.name)
            if category:
                query = query.where(MaterialType.category == category)

            result = await self.session.execute(query)
            records = result.scalars().all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get material types: {e}")
            return []

    async def get_by_id(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Get a material type by ID."""
        try:
            result = await self.session.execute(
                select(MaterialType).where(MaterialType.id == type_id)
            )
            record = result.scalar_one_or_none()
            return self._to_dict(record) if record else None
        except Exception as e:
            logger.error(f"Failed to get material type {type_id}: {e}")
            return None

    async def update(self, type_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a material type."""
        try:
            values = {}
            if "name" in data and data["name"] is not None:
                values["name"] = data["name"]
            if "category" in data and data["category"] is not None:
                values["category"] = data["category"]
            if "description" in data:
                values["description"] = data["description"]
            if "supplier" in data:
                values["supplier"] = data["supplier"]
            if "unitCost" in data:
                values["unit_cost"] = data["unitCost"]
            if "unit" in data:
                values["unit"] = data["unit"]
            if "attributes" in data:
                values["attributes"] = data["attributes"]

            values["updated_at"] = datetime.now(timezone.utc)

            await self.session.execute(
                update(MaterialType).where(MaterialType.id == type_id).values(**values)
            )
            await self.session.commit()
            return await self.get_by_id(type_id)
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update material type {type_id}: {e}")
            return None

    async def delete(self, type_id: str) -> bool:
        """Delete a material type."""
        try:
            result = await self.session.execute(
                delete(MaterialType).where(MaterialType.id == type_id)
            )
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete material type {type_id}: {e}")
            return False

    def _to_dict(self, record: MaterialType) -> Dict[str, Any]:
        """Convert SQLAlchemy model to frontend-compatible dict."""
        return {
            "id": str(record.id),
            "name": record.name,
            "category": record.category,
            "description": record.description,
            "supplier": record.supplier,
            "unitCost": record.unit_cost,
            "unit": record.unit,
            "attributes": record.attributes or [],
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
