"""
API routes for substrate management using PostgreSQL.
Provides RESTful endpoints for substrate types and batches.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.substrate.models import (
    SubstrateTypeResponse,
    SubstrateBatchResponse,
    SubstrateAttribute
)
from src.substrate.service import SubstrateService
from src.substrate.repository import SubstrateRepository
from src.database.postgresql import get_async_session
from pydantic import BaseModel

router = APIRouter(prefix="/api/substrate", tags=["substrate"])

# Request/Response models for API
class SubstrateTypeCreate(BaseModel):
    name: str
    category: str  # sewage_sludge, pig_manure, chicken_manure, sawdust, other
    description: Optional[str] = None
    custom_attributes: Optional[dict] = None

class SubstrateMixComponentCreate(BaseModel):
    substrate_type_id: str
    ratio: float  # This will be converted to ratio_percentage

class SubstrateBatchCreate(BaseModel):
    farm_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    components: List[SubstrateMixComponentCreate]
    total_weight: Optional[float] = None
    weight_unit: Optional[str] = "kg"
    batch_number: Optional[str] = None
    location: Optional[str] = None
    attributes: Optional[List[SubstrateAttribute]] = []

class SubstrateBatchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    total_weight: Optional[float] = None
    attributes: Optional[List[SubstrateAttribute]] = None
    change_reason: Optional[str] = None
    changed_by: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str
    change_reason: Optional[str] = None
    changed_by: Optional[str] = None

# Dependency to get service
async def get_substrate_service(session: AsyncSession = Depends(get_async_session)) -> SubstrateService:
    repository = SubstrateRepository(session)
    return SubstrateService(repository)

# Substrate Type endpoints
@router.post("/types", response_model=SubstrateTypeResponse, status_code=201)
async def create_substrate_type(
    substrate_type: SubstrateTypeCreate,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Create a new substrate type."""
    result = await service.create_substrate_type(
        name=substrate_type.name,
        category=substrate_type.category,
        description=substrate_type.description,
        custom_attributes=substrate_type.custom_attributes
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create substrate type")
    
    return result

@router.get("/types", response_model=List[SubstrateTypeResponse])
async def get_all_substrate_types(
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get all substrate types."""
    return await service.get_all_substrate_types()

@router.get("/types/{substrate_type_id}", response_model=SubstrateTypeResponse)
async def get_substrate_type(
    substrate_type_id: str = Path(..., description="The ID of the substrate type"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get a substrate type by ID."""
    result = await service.get_substrate_type(substrate_type_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Substrate type not found")
    
    return result

@router.put("/types/{substrate_type_id}", response_model=SubstrateTypeResponse)
async def update_substrate_type(
    substrate_type_update: SubstrateTypeCreate,
    substrate_type_id: str = Path(..., description="The ID of the substrate type"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Update a substrate type."""
    result = await service.update_substrate_type(
        substrate_type_id=substrate_type_id,
        name=substrate_type_update.name,
        category=substrate_type_update.category,
        description=substrate_type_update.description,
        custom_attributes=substrate_type_update.custom_attributes
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Substrate type not found or update failed")
    
    return result

@router.delete("/types/{substrate_type_id}", response_model=bool)
async def delete_substrate_type(
    substrate_type_id: str = Path(..., description="The ID of the substrate type"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Delete a substrate type."""
    success = await service.delete_substrate_type(substrate_type_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete substrate type. It may be in use.")
    
    return success

# Substrate Batch endpoints
@router.post("/batches", response_model=SubstrateBatchResponse, status_code=201)
async def create_substrate_batch(
    batch: SubstrateBatchCreate,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Create a new substrate batch."""
    # Generate batch name if not provided
    batch_name = batch.name or f"Batch-{batch.batch_number or 'New'}"
    
    result = await service.create_substrate_batch(
        farm_id=batch.farm_id,
        batch_name=batch_name,
        components=[{"substrate_type_id": c.substrate_type_id, "ratio": c.ratio} for c in batch.components],
        batch_number=batch.batch_number,
        description=batch.description,
        total_weight=batch.total_weight or 0.0,
        weight_unit=batch.weight_unit or "kg",
        storage_location=batch.location,
        status="active"
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create substrate batch")
    
    return result

@router.get("/batches", response_model=List[SubstrateBatchResponse])
async def get_batches_by_farm(
    farm_id: str = Query(..., description="The ID of the farm"),
    active_only: bool = Query(False, description="Filter for active batches only"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get substrate batches for a farm."""
    if active_only:
        return await service.get_active_batches_by_farm(farm_id)
    else:
        return await service.get_all_batches_by_farm(farm_id)

@router.get("/batches/{batch_id}", response_model=SubstrateBatchResponse)
async def get_substrate_batch(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get a substrate batch by ID."""
    result = await service.get_substrate_batch(batch_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    return result

@router.patch("/batches/{batch_id}", response_model=SubstrateBatchResponse)
async def update_substrate_batch(
    update_data: SubstrateBatchUpdate,
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Update a substrate batch."""
    # Get current batch
    current_batch = await service.get_substrate_batch(batch_id)
    if not current_batch:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    # Prepare update parameters
    batch_name = update_data.name if update_data.name is not None else current_batch.batch_name
    description = update_data.description if update_data.description is not None else current_batch.description
    status = update_data.status if update_data.status is not None else current_batch.status
    storage_location = update_data.location if update_data.location is not None else current_batch.storage_location
    total_weight = update_data.total_weight if update_data.total_weight is not None else current_batch.total_weight
    
    # Convert components back to dict format
    components = [
        {"substrate_type_id": comp.substrate_type_id, "ratio_percentage": comp.ratio_percentage}
        for comp in current_batch.components
    ]
    
    # Update batch
    result = await service.update_substrate_batch(
        batch_id=batch_id,
        farm_id=current_batch.farm_id,
        batch_name=batch_name,
        components=components,
        batch_number=current_batch.batch_number,
        description=description,
        total_weight=total_weight,
        weight_unit=current_batch.weight_unit,
        storage_location=storage_location,
        status=status
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update substrate batch")
    
    return result

@router.patch("/batches/{batch_id}/status", response_model=bool)
async def update_batch_status(
    status_update: StatusUpdate,
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Update the status of a substrate batch."""
    success = await service.update_batch_status(
        batch_id=batch_id,
        new_status=status_update.status,
        change_reason=status_update.change_reason,
        changed_by=status_update.changed_by
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update batch status")
    
    return success

@router.delete("/batches/{batch_id}", response_model=bool)
async def delete_substrate_batch(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Delete a substrate batch."""
    success = await service.delete_substrate_batch(batch_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Failed to delete substrate batch")
    
    return success

@router.get("/batches/{batch_id}/history", response_model=List)
async def get_batch_history(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get the change history for a substrate batch."""
    # Check if batch exists
    batch = await service.get_substrate_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    return await service.get_batch_change_history(batch_id)
