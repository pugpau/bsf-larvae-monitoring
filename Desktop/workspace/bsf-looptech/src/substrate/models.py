"""
Data models for substrate management in BSF Larvae Monitoring System.
Includes both API models and database response models.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class SubstrateTypeEnum(str, Enum):
    """Enumeration of standard substrate types."""
    SEWAGE_SLUDGE = "sewage_sludge"
    PIG_MANURE = "pig_manure"
    CHICKEN_MANURE = "chicken_manure"
    SAWDUST = "sawdust"
    OTHER = "other"


class SubstrateAttribute(BaseModel):
    """
    Model representing attributes of a substrate.
    These are detailed conditions or properties of a substrate.
    """
    name: str
    value: Union[str, float, int, bool]
    unit: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "moisture_content",
                "value": 65.5,
                "unit": "%",
                "description": "Percentage of water content in the substrate"
            }
        }


class SubstrateType(BaseModel):
    """
    Model representing a type of substrate used in BSF cultivation.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: SubstrateTypeEnum
    description: Optional[str] = None
    attributes: List[SubstrateAttribute] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Municipal Sewage Sludge",
                "type": "sewage_sludge",
                "description": "Processed sewage sludge from municipal treatment plant",
                "attributes": [
                    {
                        "name": "moisture_content",
                        "value": 65.5,
                        "unit": "%"
                    },
                    {
                        "name": "pH",
                        "value": 6.8,
                        "unit": "pH"
                    }
                ]
            }
        }


class SubstrateMixComponent(BaseModel):
    """
    Model representing a component in a substrate mix.
    """
    substrate_type_id: str
    ratio: float  # Percentage (0-100)
    
    @validator('ratio')
    def validate_ratio(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Ratio must be between 0 and 100')
        return v


class SubstrateBatch(BaseModel):
    """
    Model representing a batch of substrate mix used in BSF cultivation.
    Tracks the composition, creation time, and usage.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    farm_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    components: List[SubstrateMixComponent]
    total_weight: Optional[float] = None
    weight_unit: Optional[str] = "kg"
    batch_number: Optional[str] = None
    production_date: datetime = Field(default_factory=datetime.utcnow)
    expiration_date: Optional[datetime] = None
    status: str = "active"  # active, depleted, expired, etc.
    location: Optional[str] = None
    notes: Optional[str] = None
    attributes: List[SubstrateAttribute] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('components')
    def validate_components_ratio_sum(cls, v):
        total_ratio = sum(comp.ratio for comp in v)
        if not (99.5 <= total_ratio <= 100.5):  # Allow small rounding errors
            raise ValueError(f'Sum of component ratios must be 100%, got {total_ratio}%')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "farm_id": "farm123",
                "name": "Spring 2025 Mix #1",
                "description": "Standard mix for spring season",
                "components": [
                    {
                        "substrate_type_id": "550e8400-e29b-41d4-a716-446655440000",
                        "ratio": 70.0
                    },
                    {
                        "substrate_type_id": "550e8400-e29b-41d4-a716-446655440002",
                        "ratio": 30.0
                    }
                ],
                "total_weight": 500,
                "weight_unit": "kg",
                "batch_number": "B2025-001",
                "production_date": "2025-03-01T00:00:00Z",
                "status": "active",
                "location": "Storage Area A"
            }
        }


class SubstrateChangeLog(BaseModel):
    """
    Model for tracking changes to substrate batches.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    change_type: str  # created, updated, depleted, etc.
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "batch_id": "550e8400-e29b-41d4-a716-446655440001",
                "change_type": "updated",
                "previous_state": {
                    "status": "active",
                    "total_weight": 500
                },
                "new_state": {
                    "status": "active",
                    "total_weight": 450
                },
                "changed_by": "user123",
                "change_reason": "Used 50kg for feeding area B",
                "timestamp": "2025-03-15T14:30:00Z"
            }
        }


# PostgreSQL Repository Models

class SubstrateTypeCreate(BaseModel):
    """Model for creating a substrate type."""
    name: str
    category: str  # sewage_sludge, pig_manure, chicken_manure, sawdust, other
    description: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class SubstrateTypeResponse(BaseModel):
    """Response model for substrate type."""
    id: str
    name: str
    category: str
    description: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class SubstrateComponentCreate(BaseModel):
    """Model for creating substrate batch components."""
    substrate_type_id: str
    ratio_percentage: float


class SubstrateComponent(BaseModel):
    """Model for substrate batch components with details."""
    substrate_type_id: str
    substrate_type_name: str
    ratio_percentage: float
    weight: Optional[float] = None


class SubstrateBatchCreate(BaseModel):
    """Model for creating a substrate batch."""
    farm_id: str
    batch_name: str
    batch_number: Optional[str] = None
    description: Optional[str] = None
    total_weight: float
    weight_unit: str = "kg"
    storage_location: Optional[str] = None
    status: str = "active"
    components: List[SubstrateComponentCreate]


class SubstrateBatchResponse(BaseModel):
    """Response model for substrate batch."""
    id: str
    farm_id: str
    batch_name: str
    batch_number: Optional[str] = None
    description: Optional[str] = None
    total_weight: float
    weight_unit: str
    storage_location: Optional[str] = None
    status: str
    components: List[SubstrateComponent]
    sensor_device_ids: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True