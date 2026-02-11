"""
Pydantic models for waste treatment records and material types.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Waste Record Models ──

class AnalysisData(BaseModel):
    """Heavy metal and physical property analysis results."""
    pH: Optional[float] = None
    moisture: Optional[float] = None
    ignitionLoss: Optional[float] = None
    Pb: Optional[float] = None
    As: Optional[float] = None
    Cd: Optional[float] = None
    Cr6: Optional[float] = None
    Hg: Optional[float] = None
    Se: Optional[float] = None
    F: Optional[float] = None
    B: Optional[float] = None


class FormulationData(BaseModel):
    """Formulation (solidifier + suppressor) details."""
    solidifierType: Optional[str] = None
    solidifierAmount: Optional[float] = None
    solidifierUnit: Optional[str] = "kg/t"
    suppressorType: Optional[str] = None
    suppressorAmount: Optional[float] = None
    suppressorUnit: Optional[str] = "kg/t"


class ElutionResultData(BaseModel):
    """Elution test results."""
    Pb: Optional[float] = None
    As: Optional[float] = None
    Cd: Optional[float] = None
    Cr6: Optional[float] = None
    Hg: Optional[float] = None
    Se: Optional[float] = None
    F: Optional[float] = None
    B: Optional[float] = None
    passed: Optional[bool] = None


class RecommendationRequest(BaseModel):
    """Request model for AI formulation recommendation."""
    analysis: Dict[str, Any]
    wasteType: str


class WasteRecordCreate(BaseModel):
    """Request model for creating a waste record."""
    source: str
    deliveryDate: str  # ISO date string
    wasteType: str
    weight: Optional[float] = None
    weightUnit: str = "t"
    status: str = "pending"
    analysis: Optional[Dict[str, Any]] = None
    formulation: Optional[Dict[str, Any]] = None
    elutionResult: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class WasteRecordUpdate(BaseModel):
    """Request model for updating a waste record."""
    source: Optional[str] = None
    deliveryDate: Optional[str] = None
    wasteType: Optional[str] = None
    weight: Optional[float] = None
    weightUnit: Optional[str] = None
    status: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    formulation: Optional[Dict[str, Any]] = None
    elutionResult: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class WasteRecordResponse(BaseModel):
    """Response model for waste record."""
    id: str
    source: str
    deliveryDate: str
    wasteType: str
    weight: Optional[float] = None
    weightUnit: str
    status: str
    analysis: Optional[Dict[str, Any]] = None
    formulation: Optional[Dict[str, Any]] = None
    elutionResult: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True


# ── Material Type Models ──

class MaterialAttributeData(BaseModel):
    """Material attribute (name-value-unit triple)."""
    name: str
    value: str
    unit: Optional[str] = ""


class MaterialTypeCreate(BaseModel):
    """Request model for creating a material type."""
    name: str
    category: str  # solidifier, suppressor, waste_type
    description: Optional[str] = None
    supplier: Optional[str] = None
    unitCost: Optional[float] = None
    unit: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None


class MaterialTypeUpdate(BaseModel):
    """Request model for updating a material type."""
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    unitCost: Optional[float] = None
    unit: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None


class MaterialTypeResponse(BaseModel):
    """Response model for material type."""
    id: str
    name: str
    category: str
    description: Optional[str] = None
    supplier: Optional[str] = None
    unitCost: Optional[float] = None
    unit: Optional[str] = None
    attributes: Optional[List[Dict[str, Any]]] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
