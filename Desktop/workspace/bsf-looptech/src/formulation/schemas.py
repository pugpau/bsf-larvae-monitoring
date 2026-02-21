"""Pydantic schemas for formulation workflow."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Source / Status enums ──

SourceType = Literal["manual", "ml", "similarity", "rule", "optimization", "recipe"]
FormulationStatus = Literal["proposed", "accepted", "applied", "verified", "rejected"]


# ── Request schemas ──


class FormulationRecordCreate(BaseModel):
    waste_record_id: UUID
    recipe_id: Optional[UUID] = None
    recipe_version: Optional[int] = None
    source_type: SourceType = "manual"
    planned_formulation: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    reasoning: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=2000)


class FormulationRecordUpdate(BaseModel):
    recipe_id: Optional[UUID] = None
    recipe_version: Optional[int] = None
    planned_formulation: Optional[Dict[str, Any]] = None
    actual_formulation: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class StatusTransitionRequest(BaseModel):
    status: Literal["accepted", "applied", "verified", "rejected"] = Field(
        ..., description="Target status"
    )
    actual_formulation: Optional[Dict[str, Any]] = None
    elution_result: Optional[Dict[str, Any]] = None
    elution_passed: Optional[bool] = None
    actual_cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class RecommendRequest(BaseModel):
    waste_record_id: UUID
    top_k: int = Field(3, ge=1, le=10)


# ── Response schemas ──


class FormulationRecordResponse(BaseModel):
    id: UUID
    waste_record_id: UUID
    recipe_id: Optional[UUID] = None
    recipe_version: Optional[int] = None
    prediction_id: Optional[UUID] = None
    source_type: str
    status: str

    planned_formulation: Optional[Dict[str, Any]] = None
    actual_formulation: Optional[Dict[str, Any]] = None
    elution_result: Optional[Dict[str, Any]] = None
    elution_passed: Optional[bool] = None

    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    confidence: Optional[float] = None
    reasoning: Optional[List[str]] = None
    notes: Optional[str] = None
    created_by: Optional[UUID] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Joined fields (enriched by repository)
    waste_type: Optional[str] = None
    waste_source: Optional[str] = None
    recipe_name: Optional[str] = None

    model_config = {"from_attributes": True}


class RecommendResponse(BaseModel):
    """Response for recommend endpoint — list of candidate formulations."""
    candidates: List[FormulationRecordResponse]
    waste_record_id: UUID
    waste_type: Optional[str] = None
