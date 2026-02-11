"""Pydantic schemas for ML pipeline requests, responses, and configuration."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration for model training."""
    test_size: float = Field(0.2, ge=0.1, le=0.5)
    n_estimators: int = Field(100, ge=10, le=500)
    max_depth: Optional[int] = Field(None, ge=2, le=50)
    min_samples_split: int = Field(5, ge=2, le=20)
    cv_folds: int = Field(5, ge=2, le=10)
    use_smote: bool = True
    include_synthetic: bool = True
    synthetic_count: int = Field(200, ge=50, le=1000)
    random_state: int = 42


class PredictionRequest(BaseModel):
    """Request body for formulation prediction."""
    analysis: Dict[str, Any]
    waste_type: str
    waste_record_id: Optional[str] = None


class PredictionResponse(BaseModel):
    """Response body for formulation prediction."""
    recommendation: Dict[str, Any]
    confidence: float
    method: str  # ml, similarity, rule
    reasoning: List[str]
    model_version: Optional[int] = None
    similar_records: List[Dict[str, Any]] = Field(default_factory=list)


class ElutionPredictionRequest(BaseModel):
    """Request body for elution test outcome prediction."""
    analysis: Dict[str, Any]
    formulation: Dict[str, Any]


class ElutionPredictionResponse(BaseModel):
    """Response body for elution test prediction."""
    passed: bool
    confidence: float
    method: str
    metal_predictions: Dict[str, float] = Field(default_factory=dict)
    reasoning: List[str] = Field(default_factory=list)


class ModelMetadata(BaseModel):
    """ML model metadata for API responses."""
    id: str
    name: str
    model_type: str
    version: int
    training_records: int
    metrics: Dict[str, Any]
    is_active: bool
    created_at: str


class TrainingReport(BaseModel):
    """Report returned after model training."""
    success: bool
    real_records: int
    synthetic_records: int
    total_records: int
    classifier_metrics: Dict[str, float] = Field(default_factory=dict)
    regressor_metrics: Dict[str, float] = Field(default_factory=dict)
    model_ids: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class OptimizationRequest(BaseModel):
    """Request body for cost-optimised formulation."""
    analysis: Dict[str, Any]
    waste_type: str
    waste_weight: float = Field(1.0, gt=0)
    target_strength: Optional[float] = None
    max_budget: Optional[float] = None
    candidate_solidifiers: Optional[List[str]] = None
    candidate_suppressants: Optional[List[str]] = None


class CostBreakdown(BaseModel):
    """Cost breakdown for a single material in optimisation result."""
    material_name: str
    material_type: str  # solidifier, suppressant
    amount: float
    unit: str
    unit_cost: float
    total_cost: float


class OptimizationResponse(BaseModel):
    """Response body for cost-optimised formulation."""
    status: str  # optimal, infeasible, error
    recommendation: Dict[str, Any] = Field(default_factory=dict)
    total_cost: float = 0.0
    cost_breakdown: List[CostBreakdown] = Field(default_factory=list)
    constraints_satisfied: Dict[str, Any] = Field(default_factory=dict)
    solver_time_ms: float = 0.0
    reasoning: List[str] = Field(default_factory=list)
