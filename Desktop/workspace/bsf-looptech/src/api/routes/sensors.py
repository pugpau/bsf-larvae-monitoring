"""
API routes for sensor data management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.sensors.models import (
    SensorReadingCreate, SensorDeviceCreate, SensorAlertCreate, SensorThresholdCreate,
    SensorReadingResponse, SensorDeviceResponse, SensorAlertResponse, SensorThresholdResponse,
    SensorDeviceUpdate, SensorAlertUpdate, SensorThresholdUpdate
)
from src.sensors.service import SensorService

router = APIRouter(prefix="/sensors", tags=["sensors"])

# Dependency
def get_sensor_service():
    return SensorService()

# Sensor Reading endpoints
@router.post("/readings", response_model=SensorReadingResponse, status_code=201)
async def create_sensor_reading(
    reading: SensorReadingCreate,
    service: SensorService = Depends(get_sensor_service)
):
    """Create a new sensor reading."""
    result = service.create_sensor_reading(reading)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create sensor reading")
    
    return result

@router.get("/readings", response_model=List[SensorReadingResponse])
async def get_sensor_readings(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    substrate_batch_id: Optional[str] = Query(None, description="Filter by substrate batch ID"),
    start_time: Optional[str] = Query(None, description="Start time for query range (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for query range (ISO format)"),
    limit: int = Query(100, description="Maximum number of records to return"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get sensor readings with optional filters."""
    try:
        # Parse time parameters if provided
        start_time_parsed = None
        end_time_parsed = None
        
        if start_time:
            try:
                start_time_parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        if end_time:
            try:
                end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Get readings
        results = service.get_sensor_readings(
            farm_id=farm_id,
            device_type=device_type,
            device_id=device_id,
            measurement_type=measurement_type,
            location=location,
            substrate_batch_id=substrate_batch_id,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            limit=limit
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor readings: {str(e)}")

@router.get("/readings/latest", response_model=Dict[str, SensorReadingResponse])
async def get_latest_readings(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get latest readings for each device."""
    try:
        results = service.get_latest_readings_by_device(
            farm_id=farm_id,
            device_type=device_type,
            location=location
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest readings: {str(e)}")

@router.get("/readings/summary", response_model=Dict[str, Dict[str, float]])
async def get_readings_summary(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    substrate_batch_id: Optional[str] = Query(None, description="Filter by substrate batch ID"),
    start_time: Optional[str] = Query(None, description="Start time for query range (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for query range (ISO format)"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get summary statistics for sensor readings."""
    try:
        # Parse time parameters if provided
        start_time_parsed = None
        end_time_parsed = None
        
        if start_time:
            try:
                start_time_parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        if end_time:
            try:
                end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Get summary
        results = service.get_readings_summary(
            farm_id=farm_id,
            device_type=device_type,
            measurement_type=measurement_type,
            location=location,
            substrate_batch_id=substrate_batch_id,
            start_time=start_time_parsed,
            end_time=end_time_parsed
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving readings summary: {str(e)}")

# Sensor Device endpoints
@router.post("/devices", response_model=SensorDeviceResponse, status_code=201)
async def create_sensor_device(
    device: SensorDeviceCreate,
    service: SensorService = Depends(get_sensor_service)
):
    """Create a new sensor device."""
    result = service.create_sensor_device(device)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create sensor device")
    
    return result

@router.get("/devices", response_model=List[SensorDeviceResponse])
async def get_sensor_devices(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    location: Optional[str] = Query(None, description="Filter by location"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get sensor devices with optional filters."""
    try:
        results = service.get_sensor_devices(
            farm_id=farm_id,
            device_type=device_type,
            device_id=device_id,
            status=status,
            location=location
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor devices: {str(e)}")

@router.get("/devices/{device_id}", response_model=SensorDeviceResponse)
async def get_sensor_device(
    farm_id: str = Query(..., description="The farm ID"),
    device_id: str = Path(..., description="The device ID"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get a sensor device by ID."""
    result = service.get_sensor_device(farm_id, device_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Sensor device not found")
    
    return result

@router.patch("/devices/{device_id}", response_model=bool)
async def update_sensor_device(
    farm_id: str = Query(..., description="The farm ID"),
    device_id: str = Path(..., description="The device ID"),
    update_data: SensorDeviceUpdate = None,
    service: SensorService = Depends(get_sensor_service)
):
    """Update a sensor device."""
    result = service.update_sensor_device(farm_id, device_id, update_data)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update sensor device")
    
    return result

# Sensor Alert endpoints
@router.post("/alerts", response_model=SensorAlertResponse, status_code=201)
async def create_sensor_alert(
    alert: SensorAlertCreate,
    service: SensorService = Depends(get_sensor_service)
):
    """Create a new sensor alert."""
    result = service.create_sensor_alert(alert)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create sensor alert")
    
    return result

@router.get("/alerts", response_model=List[SensorAlertResponse])
async def get_sensor_alerts(
    farm_id: str = Query(..., description="The farm ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    substrate_batch_id: Optional[str] = Query(None, description="Filter by substrate batch ID"),
    start_time: Optional[str] = Query(None, description="Start time for query range (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for query range (ISO format)"),
    limit: int = Query(100, description="Maximum number of records to return"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get sensor alerts with optional filters."""
    try:
        # Parse time parameters if provided
        start_time_parsed = None
        end_time_parsed = None
        
        if start_time:
            try:
                start_time_parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        if end_time:
            try:
                end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Get alerts
        results = service.get_sensor_alerts(
            farm_id=farm_id,
            status=status,
            device_type=device_type,
            device_id=device_id,
            measurement_type=measurement_type,
            alert_type=alert_type,
            location=location,
            substrate_batch_id=substrate_batch_id,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            limit=limit
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor alerts: {str(e)}")

@router.patch("/alerts/{alert_id}", response_model=bool)
async def update_alert_status(
    alert_id: str = Path(..., description="The alert ID"),
    update_data: SensorAlertUpdate = None,
    service: SensorService = Depends(get_sensor_service)
):
    """Update the status of a sensor alert."""
    result = service.update_alert_status(alert_id, update_data)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update alert status")
    
    return result

@router.get("/alerts/count", response_model=Dict[str, int])
async def get_active_alerts_count(
    farm_id: str = Query(..., description="The farm ID"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get count of active alerts by type."""
    try:
        results = service.get_active_alerts_count(farm_id)
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving active alerts count: {str(e)}")

# Sensor Threshold endpoints
@router.post("/thresholds", response_model=SensorThresholdResponse, status_code=201)
async def create_sensor_threshold(
    threshold: SensorThresholdCreate,
    service: SensorService = Depends(get_sensor_service)
):
    """Create a new sensor threshold."""
    result = service.create_sensor_threshold(threshold)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create sensor threshold")
    
    return result

@router.get("/thresholds", response_model=List[SensorThresholdResponse])
async def get_sensor_thresholds(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    substrate_batch_id: Optional[str] = Query(None, description="Filter by substrate batch ID"),
    service: SensorService = Depends(get_sensor_service)
):
    """Get sensor thresholds with optional filters."""
    try:
        results = service.get_sensor_thresholds(
            farm_id=farm_id,
            device_type=device_type,
            measurement_type=measurement_type,
            location=location,
            substrate_batch_id=substrate_batch_id
        )
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor thresholds: {str(e)}")

@router.patch("/thresholds", response_model=bool)
async def update_sensor_threshold(
    farm_id: str = Query(..., description="The farm ID"),
    device_type: str = Query(..., description="The device type"),
    measurement_type: str = Query(..., description="The measurement type"),
    update_data: SensorThresholdUpdate = None,
    location: Optional[str] = Query(None, description="Filter by location"),
    substrate_batch_id: Optional[str] = Query(None, description="Filter by substrate batch ID"),
    service: SensorService = Depends(get_sensor_service)
):
    """Update a sensor threshold."""
    result = service.update_sensor_threshold(
        farm_id=farm_id,
        device_type=device_type,
        measurement_type=measurement_type,
        update_data=update_data,
        location=location,
        substrate_batch_id=substrate_batch_id
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update sensor threshold")
    
    return result

# MQTT Message Processing endpoint
@router.post("/mqtt/process", response_model=bool)
async def process_mqtt_message(
    topic: str = Query(..., description="The MQTT topic"),
    payload: Dict[str, Any] = None,
    service: SensorService = Depends(get_sensor_service)
):
    """Process an MQTT message and save sensor reading."""
    result = service.process_mqtt_message(topic, payload)
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to process MQTT message")
    
    return result
