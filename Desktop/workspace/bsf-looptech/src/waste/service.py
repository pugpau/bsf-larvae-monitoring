"""
Service layer for waste treatment records and material types.
Encapsulates business logic between API routes and repository.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from src.waste.repository import WasteRepository, MaterialTypeRepository

logger = logging.getLogger(__name__)

# Regulatory thresholds (土壌汚染対策法 溶出基準)
ELUTION_THRESHOLDS = {
    "Pb": 0.01,
    "As": 0.01,
    "Cd": 0.003,
    "Cr6": 0.05,
    "Hg": 0.0005,
    "Se": 0.01,
    "F": 0.8,
    "B": 1.0,
}


class WasteService:
    """Service for waste record operations with business logic."""

    def __init__(self, repository: WasteRepository):
        self.repository = repository

    async def create_record(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a waste record. Auto-sets status based on provided data."""
        if data.get("analysis") and any(
            v is not None for k, v in data["analysis"].items() if k != "passed"
        ):
            if data.get("status") == "pending":
                data = {**data, "status": "analyzed"}

        return await self.repository.create(data)

    async def get_all_records(
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
        """Get waste records with search, filters, pagination. Returns (items, total)."""
        return await self.repository.get_all(
            q=q, status=status, waste_type=waste_type, source=source,
            sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset,
        )

    async def get_all_for_export(
        self,
        status: Optional[str] = None,
        waste_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all records without pagination (for CSV export)."""
        return await self.repository.get_all_for_export(
            status=status, waste_type=waste_type, source=source,
        )

    async def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single waste record."""
        return await self.repository.get_by_id(record_id)

    async def update_record(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a waste record."""
        return await self.repository.update(record_id, data)

    async def delete_record(self, record_id: str) -> bool:
        """Delete a waste record."""
        return await self.repository.delete(record_id)

    def evaluate_elution(self, elution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate elution test results against regulatory thresholds.

        Returns the elution data with `passed` field computed.
        """
        result = {**elution_data}
        passed = True
        for metal, limit in ELUTION_THRESHOLDS.items():
            value = elution_data.get(metal)
            if value is not None and value > limit:
                passed = False
                break
        result["passed"] = passed
        return result


class MaterialTypeService:
    """Service for material type master operations."""

    def __init__(self, repository: MaterialTypeRepository):
        self.repository = repository

    async def create_type(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a material type."""
        return await self.repository.create(data)

    async def get_all_types(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all material types."""
        return await self.repository.get_all(category=category)

    async def get_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Get a single material type."""
        return await self.repository.get_by_id(type_id)

    async def update_type(self, type_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a material type."""
        return await self.repository.update(type_id, data)

    async def delete_type(self, type_id: str) -> bool:
        """Delete a material type."""
        return await self.repository.delete(type_id)
