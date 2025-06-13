"""
Models for analytics and anomaly detection system.
Defines rules, thresholds, and detection results.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


class ThresholdType(str, Enum):
    """Types of threshold comparisons."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUAL_TO = "equal_to"
    NOT_EQUAL_TO = "not_equal_to"
    BETWEEN = "between"
    OUTSIDE_RANGE = "outside_range"


class RuleSeverity(str, Enum):
    """Severity levels for anomaly detection rules."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleStatus(str, Enum):
    """Status of anomaly detection rules."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"


class AnomalyStatus(str, Enum):
    """Status of detected anomalies."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class TimeWindow(BaseModel):
    """Time window for rule evaluation."""
    value: int = Field(..., gt=0, description="Time window value")
    unit: str = Field(..., pattern="^(seconds|minutes|hours|days)$")
    
    def to_seconds(self) -> int:
        """Convert time window to seconds."""
        multipliers = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400
        }
        return self.value * multipliers[self.unit]


class ThresholdCondition(BaseModel):
    """Single threshold condition for a rule."""
    measurement_type: str
    threshold_type: ThresholdType
    value: Union[float, List[float]]  # Single value or range [min, max]
    unit: Optional[str] = None
    
    @validator('value')
    def validate_value(cls, v, values):
        threshold_type = values.get('threshold_type')
        if threshold_type in [ThresholdType.BETWEEN, ThresholdType.OUTSIDE_RANGE]:
            if not isinstance(v, list) or len(v) != 2:
                raise ValueError("BETWEEN and OUTSIDE_RANGE require a list of two values [min, max]")
            if v[0] >= v[1]:
                raise ValueError("First value must be less than second value for range conditions")
        else:
            if isinstance(v, list):
                raise ValueError(f"{threshold_type} requires a single value, not a list")
        return v


class DynamicThreshold(BaseModel):
    """Dynamic threshold based on historical data."""
    enabled: bool = False
    method: Optional[str] = Field(None, pattern="^(stddev|percentile|iqr)$")
    parameters: Optional[Dict[str, float]] = None
    learning_window: Optional[TimeWindow] = None
    update_frequency: Optional[TimeWindow] = None


class AnomalyDetectionRule(BaseModel):
    """Anomaly detection rule definition."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    farm_id: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    
    # Rule conditions
    conditions: List[ThresholdCondition]
    condition_logic: str = Field("AND", pattern="^(AND|OR)$")
    
    # Rule configuration
    severity: RuleSeverity
    status: RuleStatus = RuleStatus.ACTIVE
    evaluation_window: Optional[TimeWindow] = None
    cooldown_period: Optional[TimeWindow] = None
    
    # Dynamic thresholds
    dynamic_threshold: Optional[DynamicThreshold] = None
    
    # Actions
    send_alert: bool = True
    auto_control: bool = False
    control_commands: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "name": "High Temperature Alert",
                "description": "Alert when temperature exceeds 35°C",
                "farm_id": "farm_001",
                "conditions": [{
                    "measurement_type": "temperature",
                    "threshold_type": "greater_than",
                    "value": 35.0,
                    "unit": "celsius"
                }],
                "severity": "warning",
                "status": "active",
                "evaluation_window": {"value": 5, "unit": "minutes"},
                "cooldown_period": {"value": 30, "unit": "minutes"}
            }
        }


class ComplexRule(AnomalyDetectionRule):
    """Complex rule with multiple conditions and sub-rules."""
    sub_rules: Optional[List[UUID]] = []
    aggregation_method: Optional[str] = Field(None, pattern="^(any|all|majority|custom)$")
    custom_expression: Optional[str] = None


class AnomalyDetection(BaseModel):
    """Detected anomaly instance."""
    id: UUID = Field(default_factory=uuid4)
    rule_id: UUID
    rule_name: str
    
    # Detection details
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    measurement_type: str
    actual_value: float
    threshold_value: Union[float, List[float]]
    threshold_type: ThresholdType
    
    # Context
    farm_id: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    
    # Status
    severity: RuleSeverity
    status: AnomalyStatus = AnomalyStatus.OPEN
    
    # Resolution
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    # Additional data
    sensor_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "rule_id": "123e4567-e89b-12d3-a456-426614174000",
                "rule_name": "High Temperature Alert",
                "detected_at": "2024-01-15T10:30:00Z",
                "measurement_type": "temperature",
                "actual_value": 38.5,
                "threshold_value": 35.0,
                "threshold_type": "greater_than",
                "farm_id": "farm_001",
                "device_id": "sensor_t_001",
                "severity": "warning",
                "status": "open"
            }
        }


class RuleCreateRequest(BaseModel):
    """Request model for creating a new rule."""
    name: str
    description: Optional[str] = None
    farm_id: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    conditions: List[ThresholdCondition]
    condition_logic: str = "AND"
    severity: RuleSeverity
    evaluation_window: Optional[TimeWindow] = None
    cooldown_period: Optional[TimeWindow] = None
    dynamic_threshold: Optional[DynamicThreshold] = None
    send_alert: bool = True
    auto_control: bool = False
    control_commands: Optional[List[Dict[str, Any]]] = None
    tags: List[str] = []


class RuleUpdateRequest(BaseModel):
    """Request model for updating a rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[ThresholdCondition]] = None
    condition_logic: Optional[str] = None
    severity: Optional[RuleSeverity] = None
    status: Optional[RuleStatus] = None
    evaluation_window: Optional[TimeWindow] = None
    cooldown_period: Optional[TimeWindow] = None
    dynamic_threshold: Optional[DynamicThreshold] = None
    send_alert: Optional[bool] = None
    auto_control: Optional[bool] = None
    control_commands: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class AnomalyStatistics(BaseModel):
    """Statistics for anomaly detections."""
    total_anomalies: int = 0
    open_anomalies: int = 0
    acknowledged_anomalies: int = 0
    resolved_anomalies: int = 0
    false_positives: int = 0
    
    by_severity: Dict[str, int] = {}
    by_measurement_type: Dict[str, int] = {}
    by_device: Dict[str, int] = {}
    by_farm: Dict[str, int] = {}
    
    time_range: Optional[Dict[str, datetime]] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)