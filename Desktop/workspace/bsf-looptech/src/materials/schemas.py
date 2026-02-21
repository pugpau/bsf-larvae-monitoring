"""Pydantic schemas for Phase 1/2 material/supplier/recipe endpoints."""

from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

RecipeStatus = Literal["draft", "active", "archived"]


# ── Pagination ──

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: list[T]
    total: int
    limit: int
    offset: int


class ImportResult(BaseModel):
    """Result of a bulk import operation."""
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


# ── Supplier ──

class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = None
    waste_types: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = None
    waste_types: Optional[list[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    waste_types: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Solidification Material ──

class SolidificationMaterialCreate(BaseModel):
    name: str = Field(..., max_length=200)
    material_type: str = Field(..., max_length=50)
    base_material: Optional[str] = Field(None, max_length=200)
    effective_components: Optional[dict[str, Any]] = None
    applicable_soil_types: list[str] = Field(default_factory=list)
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = Field("kg", max_length=20)
    notes: Optional[str] = None
    is_active: bool = True


class SolidificationMaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    material_type: Optional[str] = Field(None, max_length=50)
    base_material: Optional[str] = Field(None, max_length=200)
    effective_components: Optional[dict[str, Any]] = None
    applicable_soil_types: Optional[list[str]] = None
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SolidificationMaterialResponse(BaseModel):
    id: UUID
    name: str
    material_type: str
    base_material: Optional[str] = None
    effective_components: Optional[dict[str, Any]] = None
    applicable_soil_types: list[str] = Field(default_factory=list)
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Leaching Suppressant ──

class LeachingSuppressantCreate(BaseModel):
    name: str = Field(..., max_length=200)
    suppressant_type: str = Field(..., max_length=100)
    target_metals: list[str] = Field(default_factory=list)
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    ph_range_min: Optional[float] = None
    ph_range_max: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = Field("kg", max_length=20)
    notes: Optional[str] = None
    is_active: bool = True


class LeachingSuppressantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    suppressant_type: Optional[str] = Field(None, max_length=100)
    target_metals: Optional[list[str]] = None
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    ph_range_min: Optional[float] = None
    ph_range_max: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class LeachingSuppressantResponse(BaseModel):
    id: UUID
    name: str
    suppressant_type: str
    target_metals: list[str] = Field(default_factory=list)
    min_addition_rate: Optional[float] = None
    max_addition_rate: Optional[float] = None
    ph_range_min: Optional[float] = None
    ph_range_max: Optional[float] = None
    unit_cost: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Recipe Detail ──

class RecipeDetailCreate(BaseModel):
    material_id: UUID
    material_type: str = Field(..., max_length=30)  # solidification, suppressant, other
    addition_rate: float = Field(..., gt=0)
    order_index: int = Field(0, ge=0)
    notes: Optional[str] = None


class RecipeDetailResponse(BaseModel):
    id: UUID
    recipe_id: UUID
    material_id: UUID
    material_type: str
    addition_rate: float
    order_index: int
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class RecipeVersionDetailResponse(BaseModel):
    """Detail item within a version snapshot (uses version_id, not recipe_id)."""
    id: UUID
    version_id: UUID
    material_id: UUID
    material_type: str
    addition_rate: float
    order_index: int
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Recipe ──

class RecipeCreate(BaseModel):
    name: str = Field(..., max_length=200)
    supplier_id: Optional[UUID] = None
    waste_type: str = Field(..., max_length=100)
    target_strength: Optional[float] = None
    target_elution: Optional[dict[str, Any]] = None
    status: RecipeStatus = "draft"
    notes: Optional[str] = None
    details: list[RecipeDetailCreate] = Field(default_factory=list)


class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    supplier_id: Optional[UUID] = None
    waste_type: Optional[str] = Field(None, max_length=100)
    target_strength: Optional[float] = None
    target_elution: Optional[dict[str, Any]] = None
    status: Optional[RecipeStatus] = None
    notes: Optional[str] = None
    change_summary: Optional[str] = Field(None, max_length=500)


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    supplier_id: Optional[UUID] = None
    waste_type: str
    target_strength: Optional[float] = None
    target_elution: Optional[dict[str, Any]] = None
    status: RecipeStatus
    notes: Optional[str] = None
    current_version: int = 1
    details: list[RecipeDetailResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Recipe Version ──

class RecipeVersionListItem(BaseModel):
    """Lightweight version item for history list."""
    id: UUID
    version: int
    change_summary: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecipeVersionResponse(BaseModel):
    """Full version snapshot with details."""
    id: UUID
    recipe_id: UUID
    version: int
    name: str
    supplier_id: Optional[UUID] = None
    waste_type: str
    target_strength: Optional[float] = None
    target_elution: Optional[dict[str, Any]] = None
    status: RecipeStatus
    notes: Optional[str] = None
    change_summary: Optional[str] = None
    created_by: Optional[UUID] = None
    details: list[RecipeVersionDetailResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecipeDiffField(BaseModel):
    """Single field difference between two versions."""
    field: str
    old_value: Any = None
    new_value: Any = None


class RecipeDiffResponse(BaseModel):
    """Diff between two recipe versions."""
    recipe_id: UUID
    version_from: int
    version_to: int
    header_changes: list[RecipeDiffField] = Field(default_factory=list)
    details_added: list[RecipeVersionDetailResponse] = Field(default_factory=list)
    details_removed: list[RecipeVersionDetailResponse] = Field(default_factory=list)
    details_modified: list[dict[str, Any]] = Field(default_factory=list)
