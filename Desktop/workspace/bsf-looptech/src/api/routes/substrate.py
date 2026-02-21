"""
API routes for substrate management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional
from src.substrate.models import SubstrateType, SubstrateBatch, SubstrateAttribute, SubstrateTypeEnum
from src.substrate.service import SubstrateService
from pydantic import BaseModel, Field

router = APIRouter(prefix="/substrate", tags=["substrate"])

# Request/Response models
class SubstrateTypeCreate(BaseModel):
    name: str
    type: SubstrateTypeEnum
    description: Optional[str] = None
    attributes: List[SubstrateAttribute] = []

class SubstrateMixComponentCreate(BaseModel):
    substrate_type_id: str
    ratio: float

class SubstrateBatchCreate(BaseModel):
    farm_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    components: List[SubstrateMixComponentCreate]
    total_weight: Optional[float] = None
    weight_unit: Optional[str] = "kg"
    batch_number: Optional[str] = None
    location: Optional[str] = None
    attributes: List[SubstrateAttribute] = []

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

# Dependency
def get_substrate_service():
    return SubstrateService()

# Substrate Type endpoints
@router.post("/types", response_model=SubstrateType, status_code=201)
async def create_substrate_type(
    substrate_type: SubstrateTypeCreate,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Create a new substrate type."""
    result = service.create_substrate_type(
        name=substrate_type.name,
        type_enum=substrate_type.type,
        description=substrate_type.description,
        attributes=substrate_type.attributes
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create substrate type")
    
    return result

@router.get("/types", response_model=List[SubstrateType])
async def get_all_substrate_types(
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get all substrate types."""
    return service.get_all_substrate_types()

@router.get("/types/{substrate_type_id}", response_model=SubstrateType)
async def get_substrate_type(
    substrate_type_id: str = Path(..., description="The ID of the substrate type"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get a substrate type by ID."""
    result = service.get_substrate_type(substrate_type_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Substrate type not found")
    
    return result

# Substrate Batch endpoints
@router.post("/batches", response_model=SubstrateBatch, status_code=201)
async def create_substrate_batch(
    batch: SubstrateBatchCreate,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Create a new substrate batch."""
    result = service.create_substrate_batch(
        farm_id=batch.farm_id,
        components=batch.components,
        name=batch.name,
        description=batch.description,
        total_weight=batch.total_weight,
        weight_unit=batch.weight_unit,
        batch_number=batch.batch_number,
        location=batch.location,
        attributes=batch.attributes
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create substrate batch")
    
    return result

@router.get("/batches", response_model=List[SubstrateBatch])
async def get_batches_by_farm(
    farm_id: str = Query(..., description="The ID of the farm"),
    active_only: bool = Query(False, description="Filter for active batches only"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get substrate batches for a farm."""
    if active_only:
        return service.get_active_batches_by_farm(farm_id)
    else:
        return service.get_all_batches_by_farm(farm_id)

@router.get("/batches/{batch_id}", response_model=SubstrateBatch)
async def get_substrate_batch(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get a substrate batch by ID."""
    result = service.get_substrate_batch(batch_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    return result

@router.patch("/batches/{batch_id}", response_model=bool)
async def update_substrate_batch(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    update_data: SubstrateBatchUpdate = None,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Update a substrate batch."""
    # Get current batch
    current_batch = service.get_substrate_batch(batch_id)
    if not current_batch:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    # Update fields if provided
    if update_data.name is not None:
        current_batch.name = update_data.name
    
    if update_data.description is not None:
        current_batch.description = update_data.description
    
    if update_data.status is not None:
        current_batch.status = update_data.status
    
    if update_data.location is not None:
        current_batch.location = update_data.location
    
    if update_data.total_weight is not None:
        current_batch.total_weight = update_data.total_weight
    
    if update_data.attributes is not None:
        current_batch.attributes = update_data.attributes
    
    # Update batch
    success = service.update_substrate_batch(
        batch=current_batch,
        change_reason=update_data.change_reason,
        changed_by=update_data.changed_by
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update substrate batch")
    
    return success

@router.patch("/batches/{batch_id}/status", response_model=bool)
async def update_batch_status(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    status_update: StatusUpdate = None,
    service: SubstrateService = Depends(get_substrate_service)
):
    """Update the status of a substrate batch."""
    success = service.update_batch_status(
        batch_id=batch_id,
        new_status=status_update.status,
        change_reason=status_update.change_reason,
        changed_by=status_update.changed_by
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update batch status")
    
    return success

@router.get("/batches/{batch_id}/history", response_model=List)
async def get_batch_history(
    batch_id: str = Path(..., description="The ID of the substrate batch"),
    service: SubstrateService = Depends(get_substrate_service)
):
    """Get the change history for a substrate batch."""
    # Check if batch exists
    batch = service.get_substrate_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Substrate batch not found")
    
    return service.get_batch_change_history(batch_id)