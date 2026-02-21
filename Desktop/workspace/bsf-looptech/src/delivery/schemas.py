"""Pydantic schemas for incoming materials and delivery schedules."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Incoming Material (搬入物マスター) ──


class IncomingMaterialCreate(BaseModel):
    supplier_id: UUID
    material_category: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    default_weight_unit: str = Field("t", max_length=10)
    notes: Optional[str] = None
    is_active: bool = True


class IncomingMaterialUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    material_category: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    default_weight_unit: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class IncomingMaterialResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    supplier_name: Optional[str] = None
    material_category: str
    name: str
    description: Optional[str] = None
    default_weight_unit: str = "t"
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Delivery Schedule (搬入予定) ──


class DeliveryScheduleCreate(BaseModel):
    incoming_material_id: UUID
    scheduled_date: str = Field(..., description="ISO date YYYY-MM-DD")
    estimated_weight: Optional[float] = Field(None, ge=0)
    weight_unit: str = Field("t", max_length=10)
    notes: Optional[str] = None


class DeliveryScheduleUpdate(BaseModel):
    incoming_material_id: Optional[UUID] = None
    scheduled_date: Optional[str] = None
    estimated_weight: Optional[float] = Field(None, ge=0)
    actual_weight: Optional[float] = Field(None, ge=0)
    weight_unit: Optional[str] = Field(None, max_length=10)
    notes: Optional[str] = None


class DeliveryScheduleResponse(BaseModel):
    id: UUID
    incoming_material_id: UUID
    supplier_name: Optional[str] = None
    material_category: Optional[str] = None
    material_name: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_weight: Optional[float] = None
    actual_weight: Optional[float] = None
    weight_unit: str = "t"
    status: str = "scheduled"
    waste_record_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StatusUpdateRequest(BaseModel):
    status: Literal["delivered", "cancelled"] = Field(
        ..., description="Target status: delivered or cancelled"
    )
    actual_weight: Optional[float] = Field(None, ge=0)
