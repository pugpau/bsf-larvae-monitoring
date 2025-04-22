"""
API routes for sensor data management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from database.influxdb import query_sensor_data
from pydantic import BaseModel, Field
import uuid
import json
import os
from pathlib import Path as FilePath

router = APIRouter(prefix="/sensors", tags=["sensors"])

DEVICE_DATA_FILE = FilePath("./data/sensor_devices.json")

class SensorDataResponse(BaseModel):
    time: datetime
    farm_id: str
    device_id: str
    device_type: str
    field: str
    value: float

class SensorDeviceBase(BaseModel):
    device_id: str
    device_type: str
    name: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    status: str = "inactive"
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorDeviceCreate(SensorDeviceBase):
    farm_id: str

class SensorDeviceUpdate(BaseModel):
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    z_position: Optional[float] = None
    status: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SensorDevice(SensorDeviceBase):
    id: str
    farm_id: str
    created_at: datetime
    updated_at: datetime

class SensorDeviceService:
    def __init__(self):
        self._ensure_data_dir()
        self.devices = self._load_devices()
    
    def _ensure_data_dir(self):
        """データディレクトリが存在することを確認"""
        os.makedirs(DEVICE_DATA_FILE.parent, exist_ok=True)
        if not DEVICE_DATA_FILE.exists():
            with open(DEVICE_DATA_FILE, 'w') as f:
                json.dump([], f)
    
    def _load_devices(self) -> List[Dict[str, Any]]:
        """デバイスデータをロード"""
        try:
            with open(DEVICE_DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_devices(self):
        """デバイスデータを保存"""
        with open(DEVICE_DATA_FILE, 'w') as f:
            json.dump(self.devices, f, default=str)
    
    def create_device(self, device_data: SensorDeviceCreate) -> SensorDevice:
        """新しいセンサーデバイスを作成"""
        now = datetime.utcnow()
        device = {
            "id": str(uuid.uuid4()),
            "farm_id": device_data.farm_id,
            "device_id": device_data.device_id,
            "device_type": device_data.device_type,
            "name": device_data.name,
            "location": device_data.location,
            "x_position": device_data.x_position,
            "y_position": device_data.y_position,
            "z_position": device_data.z_position,
            "status": device_data.status,
            "substrate_batch_id": device_data.substrate_batch_id,
            "metadata": device_data.metadata,
            "created_at": now,
            "updated_at": now
        }
        self.devices.append(device)
        self._save_devices()
        return SensorDevice(**device)
    
    def get_all_devices(self) -> List[SensorDevice]:
        """すべてのセンサーデバイスを取得"""
        return [SensorDevice(**device) for device in self.devices]
    
    def get_devices_by_farm(self, farm_id: str) -> List[SensorDevice]:
        """ファームIDに基づいてセンサーデバイスを取得"""
        return [SensorDevice(**device) for device in self.devices if device["farm_id"] == farm_id]
    
    def get_device(self, device_id: str) -> Optional[SensorDevice]:
        """IDに基づいてセンサーデバイスを取得"""
        for device in self.devices:
            if device["id"] == device_id:
                return SensorDevice(**device)
        return None
    
    def update_device(self, device_id: str, update_data: SensorDeviceUpdate) -> Optional[SensorDevice]:
        """センサーデバイスを更新"""
        for i, device in enumerate(self.devices):
            if device["id"] == device_id:
                for field, value in update_data.dict(exclude_unset=True).items():
                    if value is not None:
                        device[field] = value
                
                device["updated_at"] = datetime.utcnow()
                self.devices[i] = device
                self._save_devices()
                return SensorDevice(**device)
        return None
    
    def delete_device(self, device_id: str) -> bool:
        """センサーデバイスを削除"""
        for i, device in enumerate(self.devices):
            if device["id"] == device_id:
                self.devices.pop(i)
                self._save_devices()
                return True
        return False

def get_sensor_device_service():
    return SensorDeviceService()

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

@router.post("/devices", response_model=SensorDevice, status_code=201)
async def create_sensor_device(
    device: SensorDeviceCreate,
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Create a new sensor device.
    """
    try:
        result = service.create_device(device)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating sensor device: {str(e)}")

@router.get("/devices", response_model=List[SensorDevice])
async def get_sensor_devices(
    farm_id: Optional[str] = Query(None, description="Filter by farm ID"),
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Get all sensor devices, optionally filtered by farm ID.
    """
    try:
        if farm_id:
            return service.get_devices_by_farm(farm_id)
        else:
            return service.get_all_devices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor devices: {str(e)}")

@router.get("/devices/{device_id}", response_model=SensorDevice)
async def get_sensor_device(
    device_id: str = Path(..., description="The ID of the sensor device"),
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Get a sensor device by ID.
    """
    try:
        device = service.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Sensor device not found")
        return device
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sensor device: {str(e)}")

@router.patch("/devices/{device_id}", response_model=SensorDevice)
async def update_sensor_device(
    device_id: str = Path(..., description="The ID of the sensor device"),
    update_data: SensorDeviceUpdate = None,
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Update a sensor device.
    """
    try:
        device = service.update_device(device_id, update_data)
        if not device:
            raise HTTPException(status_code=404, detail="Sensor device not found")
        return device
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating sensor device: {str(e)}")

@router.delete("/devices/{device_id}", response_model=bool)
async def delete_sensor_device(
    device_id: str = Path(..., description="The ID of the sensor device"),
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Delete a sensor device.
    """
    try:
        success = service.delete_device(device_id)
        if not success:
            raise HTTPException(status_code=404, detail="Sensor device not found")
        return success
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting sensor device: {str(e)}")

@router.post("/devices/{device_id}/wakeup", status_code=200)
async def wakeup_device(
    device_id: str = Path(..., description="The device ID to wake up"),
    service: SensorDeviceService = Depends(get_sensor_device_service)
):
    """
    Wake up a sensor device.
    
    This endpoint sends a signal to activate the specified sensor device.
    """
    try:
        device = service.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Sensor device not found")
        
        update_data = SensorDeviceUpdate(status="active")
        updated_device = service.update_device(device_id, update_data)
        
        if not updated_device:
            raise HTTPException(status_code=500, detail="Failed to update device status")
        
        
        return {"success": True, "message": f"Device {device_id} has been woken up successfully."}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error waking up device: {str(e)}")
