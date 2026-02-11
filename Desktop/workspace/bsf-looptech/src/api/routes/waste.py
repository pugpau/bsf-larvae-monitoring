"""
API routes for waste treatment records and material types.
Provides RESTful endpoints aligned with the frontend data model.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.waste.repository import WasteRepository, MaterialTypeRepository
from src.waste.service import WasteService, MaterialTypeService
from src.waste.models import (
    WasteRecordCreate,
    WasteRecordUpdate,
    WasteRecordResponse,
    MaterialTypeCreate,
    MaterialTypeUpdate,
    MaterialTypeResponse,
    RecommendationRequest,
)
from src.waste.recommender import recommend_formulation
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/waste", tags=["waste"])


# ── Dependencies ──

async def get_waste_service(session: AsyncSession = Depends(get_async_session)) -> WasteService:
    return WasteService(WasteRepository(session))


async def get_material_service(session: AsyncSession = Depends(get_async_session)) -> MaterialTypeService:
    return MaterialTypeService(MaterialTypeRepository(session))


# ── Waste Record endpoints ──

@router.post("/records", status_code=201)
async def create_waste_record(
    data: WasteRecordCreate,
    service: WasteService = Depends(get_waste_service),
):
    """Create a new waste record."""
    result = await service.create_record(data.dict())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create waste record")
    return result


@router.get("/records")
async def get_waste_records(
    status: Optional[str] = Query(None),
    wasteType: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(200, le=500),
    offset: int = Query(0),
    service: WasteService = Depends(get_waste_service),
):
    """Get all waste records with optional filters."""
    return await service.get_all_records(
        status=status, waste_type=wasteType, source=source,
        limit=limit, offset=offset,
    )


@router.get("/records/{record_id}")
async def get_waste_record(
    record_id: str,
    service: WasteService = Depends(get_waste_service),
):
    """Get a waste record by ID."""
    result = await service.get_record(record_id)
    if not result:
        raise HTTPException(status_code=404, detail="Waste record not found")
    return result


@router.put("/records/{record_id}")
async def update_waste_record(
    record_id: str,
    data: WasteRecordUpdate,
    service: WasteService = Depends(get_waste_service),
):
    """Update a waste record."""
    result = await service.update_record(record_id, data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Waste record not found or update failed")
    return result


@router.delete("/records/{record_id}")
async def delete_waste_record(
    record_id: str,
    service: WasteService = Depends(get_waste_service),
):
    """Delete a waste record."""
    success = await service.delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Waste record not found")
    return {"message": "Waste record deleted"}


# ── AI Recommendation ──

@router.post("/recommend")
async def recommend(
    data: RecommendationRequest,
    service: WasteService = Depends(get_waste_service),
):
    """Get AI-recommended formulation based on waste analysis data."""
    if not data.analysis or not any(
        v is not None for v in data.analysis.values()
    ):
        raise HTTPException(status_code=400, detail="Analysis data is required")

    # Fetch past records as training history
    history = await service.get_all_records(limit=500)

    result = recommend_formulation(
        analysis=data.analysis,
        waste_type=data.wasteType,
        history=history,
    )
    return result


# ── Material Type endpoints ──

@router.post("/materials", status_code=201)
async def create_material_type(
    data: MaterialTypeCreate,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Create a new material type."""
    result = await service.create_type(data.dict())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create material type")
    return result


@router.get("/materials")
async def get_material_types(
    category: Optional[str] = Query(None),
    service: MaterialTypeService = Depends(get_material_service),
):
    """Get all material types, optionally filtered by category."""
    return await service.get_all_types(category=category)


@router.get("/materials/{type_id}")
async def get_material_type(
    type_id: str,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Get a material type by ID."""
    result = await service.get_type(type_id)
    if not result:
        raise HTTPException(status_code=404, detail="Material type not found")
    return result


@router.put("/materials/{type_id}")
async def update_material_type(
    type_id: str,
    data: MaterialTypeUpdate,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Update a material type."""
    result = await service.update_type(type_id, data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Material type not found or update failed")
    return result


@router.delete("/materials/{type_id}")
async def delete_material_type(
    type_id: str,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Delete a material type."""
    success = await service.delete_type(type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Material type not found")
    return {"message": "Material type deleted"}
