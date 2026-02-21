"""Pydantic schemas for KPI API."""

from typing import Optional

from pydantic import BaseModel


class KPIMetric(BaseModel):
    """Single KPI metric with current value, trend, and status."""

    label: str
    value: float
    unit: str
    trend: Optional[float] = None  # % change from previous period
    status: str = "normal"  # normal / warning / critical


class KPIRealtimeResponse(BaseModel):
    """All 6 KPI metrics — current values."""

    period_days: int
    processing_volume: KPIMetric
    formulation_success_rate: KPIMetric
    material_cost: KPIMetric
    ml_usage_rate: KPIMetric
    avg_processing_time: KPIMetric
    violation_rate: KPIMetric
    updated_at: str


class KPITrendPoint(BaseModel):
    """Single data point in a KPI trend series."""

    period: str  # YYYY-MM
    processing_volume: float
    success_rate: float
    material_cost: float
    ml_usage_rate: float
    avg_processing_time_hours: float
    violation_rate: float


class KPITrendsResponse(BaseModel):
    """Historical KPI trend data."""

    months: int
    data: list[KPITrendPoint]


class KPIAlert(BaseModel):
    """Single KPI alert — threshold violation or warning."""

    severity: str  # warning / critical
    metric: str
    message: str
    value: float
    threshold: float
    record_id: Optional[str] = None
    created_at: str


class KPIAlertsResponse(BaseModel):
    """Active KPI alerts."""

    alerts: list[KPIAlert]
    total: int
