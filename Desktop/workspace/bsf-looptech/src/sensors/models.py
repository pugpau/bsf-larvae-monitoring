"""
Models for sensor data management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class SensorReading(BaseModel):
    """Model for a single sensor reading."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    farm_id: str
    device_id: str
    device_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    measurement_type: str  # temperature, humidity, pressure, h2s, nh3
    value: float
    unit: str  # °C, %RH, hPa, ppm
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "farm_id": "farm123",
                "device_id": "sensor001",
                "device_type": "temperature",
                "measurement_type": "temperature",
                "value": 25.5,
                "unit": "°C",
                "location": "area1",
                "substrate_batch_id": "batch123",
                "x_position": 10.5,
                "y_position": 20.3,
                "z_position": 5.0,
                "metadata": {"calibration_date": "2025-01-01"}
            }
        }

class SensorReadingCreate(BaseModel):
    """Model for creating a sensor reading."""
    farm_id: str
    device_id: str
    device_type: str
    measurement_type: str
    value: float
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorReadingResponse(BaseModel):
    """Model for sensor reading response."""
    id: str
    farm_id: str
    device_id: str
    device_type: str
    timestamp: datetime
    measurement_type: str
    value: float
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorDevice(BaseModel):
    """Model for a sensor device."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    farm_id: str
    device_id: str
    device_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    status: str = "active"  # active, inactive, maintenance
    last_seen: Optional[datetime] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "farm_id": "farm123",
                "device_id": "sensor001",
                "device_type": "temperature",
                "name": "Temperature Sensor 1",
                "description": "Main temperature sensor for area 1",
                "location": "area1",
                "x_position": 10.5,
                "y_position": 20.3,
                "z_position": 5.0,
                "status": "active",
                "substrate_batch_id": "batch123",
                "metadata": {"model": "DHT22", "manufacturer": "Example Inc."}
            }
        }

class SensorDeviceCreate(BaseModel):
    """Model for creating a sensor device."""
    farm_id: str
    device_id: str
    device_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorDeviceUpdate(BaseModel):
    """Model for updating a sensor device."""
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    status: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorDeviceResponse(BaseModel):
    """Model for sensor device response."""
    id: str
    farm_id: str
    device_id: str
    device_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    status: str
    last_seen: Optional[datetime] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class SensorAlert(BaseModel):
    """Model for a sensor alert."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    farm_id: str
    device_id: str
    device_type: str
    measurement_type: str
    alert_type: str  # high, low, offline
    threshold: float
    actual_value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, acknowledged, resolved
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "farm_id": "farm123",
                "device_id": "sensor001",
                "device_type": "temperature",
                "measurement_type": "temperature",
                "alert_type": "high",
                "threshold": 30.0,
                "actual_value": 32.5,
                "unit": "°C",
                "status": "active",
                "location": "area1",
                "substrate_batch_id": "batch123"
            }
        }

class SensorAlertCreate(BaseModel):
    """Model for creating a sensor alert."""
    farm_id: str
    device_id: str
    device_type: str
    measurement_type: str
    alert_type: str
    threshold: float
    actual_value: float
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorAlertUpdate(BaseModel):
    """Model for updating a sensor alert."""
    status: str
    metadata: Optional[Dict[str, Any]] = None

class SensorAlertResponse(BaseModel):
    """Model for sensor alert response."""
    id: str
    farm_id: str
    device_id: str
    device_type: str
    measurement_type: str
    alert_type: str
    threshold: float
    actual_value: float
    unit: str
    timestamp: datetime
    status: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorThreshold(BaseModel):
    """Model for a sensor threshold."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    farm_id: str
    device_type: str
    measurement_type: str
    high_threshold: Optional[float] = None
    low_threshold: Optional[float] = None
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "farm_id": "farm123",
                "device_type": "temperature",
                "measurement_type": "temperature",
                "high_threshold": 30.0,
                "low_threshold": 20.0,
                "unit": "°C",
                "location": "area1"
            }
        }

class SensorThresholdCreate(BaseModel):
    """Model for creating a sensor threshold."""
    farm_id: str
    device_type: str
    measurement_type: str
    high_threshold: Optional[float] = None
    low_threshold: Optional[float] = None
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None

class SensorThresholdUpdate(BaseModel):
    """Model for updating a sensor threshold."""
    high_threshold: Optional[float] = None
    low_threshold: Optional[float] = None
    unit: Optional[str] = None
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None

class SensorThresholdResponse(BaseModel):
    """Model for sensor threshold response."""
    id: str
    farm_id: str
    device_type: str
    measurement_type: str
    high_threshold: Optional[float] = None
    low_threshold: Optional[float] = None
    unit: str
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
