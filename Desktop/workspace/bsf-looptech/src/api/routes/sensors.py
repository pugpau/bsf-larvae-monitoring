"""
API routes for sensor data management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.database.influxdb import query_sensor_data
from pydantic import BaseModel

router = APIRouter(prefix="/sensors", tags=["sensors"])

class SensorDataResponse(BaseModel):
    time: datetime
    farm_id: str
    device_id: str
    device_type: str
    field: str
    value: float

@router.get("/data", response_model=List[SensorDataResponse])
async def get_sensor_data(
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type (e.g., temperature)"),
    start_time: Optional[str] = Query(None, description="Start time for query range (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for query range (ISO format)"),
    limit: int = Query(100, description="Maximum number of records to return")
):
    """
    Get sensor data with optional filters.
    
    Returns sensor readings based on the provided filters.
    If no filters are provided, returns the most recent readings.
    """
    try:
        # Parse time parameters if provided
        start_time_parsed = None
        end_time_parsed = None
        
        if start_time:
            try:
                start_time_parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        else:
            # Default to last 24 hours if not specified
            start_time_parsed = datetime.utcnow() - timedelta(days=1)
        
        if end_time:
            try:
                end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Query data
        results = query_sensor_data(
            farm_id=farm_id,
            device_id=device_id,
            device_type=device_type,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            measurement_type=measurement_type
        )
        
        # Limit results
        if limit and len(results) > limit:
            results = results[:limit]
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor data: {str(e)}")

@router.get("/data/{farm_id}/{device_id}", response_model=List[SensorDataResponse])
async def get_device_sensor_data(
    farm_id: str = Path(..., description="The farm ID"),
    device_id: str = Path(..., description="The device ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type (e.g., temperature)"),
    start_time: Optional[str] = Query(None, description="Start time for query range (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time for query range (ISO format)"),
    limit: int = Query(100, description="Maximum number of records to return")
):
    """
    Get sensor data for a specific device.
    
    Returns sensor readings for the specified device.
    """
    try:
        # Parse time parameters if provided
        start_time_parsed = None
        end_time_parsed = None
        
        if start_time:
            try:
                start_time_parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        else:
            # Default to last 24 hours if not specified
            start_time_parsed = datetime.utcnow() - timedelta(days=1)
        
        if end_time:
            try:
                end_time_parsed = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        # Query data
        results = query_sensor_data(
            farm_id=farm_id,
            device_id=device_id,
            device_type=device_type,
            start_time=start_time_parsed,
            end_time=end_time_parsed,
            measurement_type=measurement_type
        )
        
        # Limit results
        if limit and len(results) > limit:
            results = results[:limit]
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor data: {str(e)}")

@router.get("/latest/{farm_id}", response_model=Dict[str, Dict[str, Any]])
async def get_latest_farm_data(
    farm_id: str = Path(..., description="The farm ID")
):
    """
    Get the latest sensor readings for all devices in a farm.
    
    Returns a dictionary with device IDs as keys and their latest readings as values.
    """
    try:
        # Get data from the last hour to ensure we have recent readings
        start_time = datetime.utcnow() - timedelta(hours=1)
        
        # Query data
        results = query_sensor_data(
            farm_id=farm_id,
            start_time=start_time
        )
        
        # Process results to get latest reading per device and measurement type
        latest_readings = {}
        
        for reading in results:
            device_id = reading.get("device_id")
            field = reading.get("field")
            
            if not device_id or not field:
                continue
            
            if device_id not in latest_readings:
                latest_readings[device_id] = {
                    "device_type": reading.get("device_type"),
                    "last_updated": reading.get("time"),
                    "measurements": {}
                }
            
            # Update if this reading is newer
            current_time = reading.get("time")
            if current_time > latest_readings[device_id]["last_updated"]:
                latest_readings[device_id]["last_updated"] = current_time
            
            # Add measurement
            latest_readings[device_id]["measurements"][field] = reading.get("value")
        
        return latest_readings
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest farm data: {str(e)}")