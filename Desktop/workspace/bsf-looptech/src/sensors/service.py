"""
Service for sensor data management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.sensors.models import (
    SensorReading, SensorDevice, SensorAlert, SensorThreshold,
    SensorReadingCreate, SensorDeviceCreate, SensorAlertCreate, SensorThresholdCreate,
    SensorReadingResponse, SensorDeviceResponse, SensorAlertResponse, SensorThresholdResponse,
    SensorDeviceUpdate, SensorAlertUpdate, SensorThresholdUpdate
)
from src.sensors.repository import SensorRepository

logger = logging.getLogger(__name__)

class SensorService:
    """Service for sensor data management."""
    
    def __init__(self):
        self.repository = SensorRepository()
    
    # Sensor Reading Operations
    
    def create_sensor_reading(self, reading_data: SensorReadingCreate) -> Optional[SensorReadingResponse]:
        """Create a new sensor reading."""
        try:
            # Create reading
            reading = SensorReading(
                farm_id=reading_data.farm_id,
                device_id=reading_data.device_id,
                device_type=reading_data.device_type,
                measurement_type=reading_data.measurement_type,
                value=reading_data.value,
                unit=reading_data.unit,
                location=reading_data.location,
                substrate_batch_id=reading_data.substrate_batch_id,
                metadata=reading_data.metadata
            )
            
            # Save reading
            success = self.repository.save_sensor_reading(reading)
            if not success:
                logger.error("Failed to save sensor reading")
                return None
            
            # Return reading response
            return SensorReadingResponse(
                id=reading.id,
                farm_id=reading.farm_id,
                device_id=reading.device_id,
                device_type=reading.device_type,
                timestamp=reading.timestamp,
                measurement_type=reading.measurement_type,
                value=reading.value,
                unit=reading.unit,
                location=reading.location,
                substrate_batch_id=reading.substrate_batch_id,
                metadata=reading.metadata
            )
        except Exception as e:
            logger.error(f"Error creating sensor reading: {e}")
            return None
    
    def get_sensor_readings(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        measurement_type: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SensorReadingResponse]:
        """Get sensor readings."""
        try:
            return self.repository.get_sensor_readings(
                farm_id=farm_id,
                device_type=device_type,
                device_id=device_id,
                measurement_type=measurement_type,
                location=location,
                substrate_batch_id=substrate_batch_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting sensor readings: {e}")
            return []
    
    def get_latest_readings_by_device(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, SensorReadingResponse]:
        """Get latest readings for each device."""
        try:
            # Get all devices
            devices = self.get_sensor_devices(
                farm_id=farm_id,
                device_type=device_type,
                location=location,
                status="active"
            )
            
            # Get latest reading for each device
            latest_readings = {}
            for device in devices:
                readings = self.repository.get_sensor_readings(
                    farm_id=farm_id,
                    device_id=device.device_id,
                    limit=1
                )
                if readings:
                    latest_readings[device.device_id] = readings[0]
            
            return latest_readings
        except Exception as e:
            logger.error(f"Error getting latest readings by device: {e}")
            return {}
    
    def get_readings_summary(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        measurement_type: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for sensor readings."""
        try:
            # Get readings
            readings = self.repository.get_sensor_readings(
                farm_id=farm_id,
                device_type=device_type,
                measurement_type=measurement_type,
                location=location,
                substrate_batch_id=substrate_batch_id,
                start_time=start_time,
                end_time=end_time,
                limit=1000  # Increased limit for better statistics
            )
            
            if not readings:
                return {}
            
            # Group readings by measurement type
            grouped_readings = {}
            for reading in readings:
                key = reading.measurement_type
                if key not in grouped_readings:
                    grouped_readings[key] = []
                grouped_readings[key].append(reading.value)
            
            # Calculate statistics for each measurement type
            summary = {}
            for measurement_type, values in grouped_readings.items():
                if not values:
                    continue
                
                # Calculate statistics
                min_value = min(values)
                max_value = max(values)
                avg_value = sum(values) / len(values)
                
                # Add to summary
                summary[measurement_type] = {
                    "min": min_value,
                    "max": max_value,
                    "avg": avg_value,
                    "count": len(values)
                }
            
            return summary
        except Exception as e:
            logger.error(f"Error getting readings summary: {e}")
            return {}
    
    # Sensor Device Operations
    
    def create_sensor_device(self, device_data: SensorDeviceCreate) -> Optional[SensorDeviceResponse]:
        """Create a new sensor device."""
        try:
            # Create device
            device = SensorDevice(
                farm_id=device_data.farm_id,
                device_id=device_data.device_id,
                device_type=device_data.device_type,
                name=device_data.name,
                description=device_data.description,
                location=device_data.location,
                metadata=device_data.metadata
            )
            
            # Save device
            success = self.repository.save_sensor_device(device)
            if not success:
                logger.error("Failed to save sensor device")
                return None
            
            # Return device response
            return SensorDeviceResponse(
                id=device.id,
                farm_id=device.farm_id,
                device_id=device.device_id,
                device_type=device.device_type,
                name=device.name,
                description=device.description,
                location=device.location,
                status=device.status,
                last_seen=device.last_seen,
                metadata=device.metadata,
                created_at=device.created_at,
                updated_at=device.updated_at
            )
        except Exception as e:
            logger.error(f"Error creating sensor device: {e}")
            return None
    
    def get_sensor_devices(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[SensorDeviceResponse]:
        """Get sensor devices."""
        try:
            return self.repository.get_sensor_devices(
                farm_id=farm_id,
                device_type=device_type,
                device_id=device_id,
                status=status,
                location=location
            )
        except Exception as e:
            logger.error(f"Error getting sensor devices: {e}")
            return []
    
    def get_sensor_device(self, farm_id: str, device_id: str) -> Optional[SensorDeviceResponse]:
        """Get a sensor device by ID."""
        try:
            devices = self.repository.get_sensor_devices(
                farm_id=farm_id,
                device_id=device_id
            )
            
            if not devices:
                return None
            
            return devices[0]
        except Exception as e:
            logger.error(f"Error getting sensor device: {e}")
            return None
    
    def update_sensor_device(self, farm_id: str, device_id: str, update_data: SensorDeviceUpdate) -> bool:
        """Update a sensor device."""
        try:
            # Get current device
            devices = self.repository.get_sensor_devices(
                farm_id=farm_id,
                device_id=device_id
            )
            
            if not devices:
                logger.error(f"Device not found for update: {device_id}")
                return False
            
            device = devices[0]
            
            # Update fields
            if update_data.name is not None:
                device.name = update_data.name
            if update_data.description is not None:
                device.description = update_data.description
            if update_data.location is not None:
                device.location = update_data.location
            if update_data.x_position is not None:
                device.x_position = update_data.x_position
            if update_data.y_position is not None:
                device.y_position = update_data.y_position
            if update_data.z_position is not None:
                device.z_position = update_data.z_position
            if update_data.status is not None:
                device.status = update_data.status
            if update_data.metadata is not None:
                if device.metadata:
                    device.metadata.update(update_data.metadata)
                else:
                    device.metadata = update_data.metadata
            
            # Update timestamp
            device.updated_at = datetime.utcnow()
            
            # Save device
            return self.repository.save_sensor_device(SensorDevice(**device.dict()))
        except Exception as e:
            logger.error(f"Error updating sensor device: {e}")
            return False
    
    # Sensor Alert Operations
    
    def create_sensor_alert(self, alert_data: SensorAlertCreate) -> Optional[SensorAlertResponse]:
        """Create a new sensor alert."""
        try:
            # Create alert
            alert = SensorAlert(
                farm_id=alert_data.farm_id,
                device_id=alert_data.device_id,
                device_type=alert_data.device_type,
                measurement_type=alert_data.measurement_type,
                alert_type=alert_data.alert_type,
                threshold=alert_data.threshold,
                actual_value=alert_data.actual_value,
                unit=alert_data.unit,
                location=alert_data.location,
                substrate_batch_id=alert_data.substrate_batch_id,
                metadata=alert_data.metadata
            )
            
            # Save alert
            success = self.repository.save_sensor_alert(alert)
            if not success:
                logger.error("Failed to save sensor alert")
                return None
            
            # Return alert response
            return SensorAlertResponse(
                id=alert.id,
                farm_id=alert.farm_id,
                device_id=alert.device_id,
                device_type=alert.device_type,
                measurement_type=alert.measurement_type,
                alert_type=alert.alert_type,
                threshold=alert.threshold,
                actual_value=alert.actual_value,
                unit=alert.unit,
                timestamp=alert.timestamp,
                status=alert.status,
                location=alert.location,
                substrate_batch_id=alert.substrate_batch_id,
                metadata=alert.metadata
            )
        except Exception as e:
            logger.error(f"Error creating sensor alert: {e}")
            return None
    
    def get_sensor_alerts(
        self, 
        farm_id: str, 
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        measurement_type: Optional[str] = None,
        alert_type: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SensorAlertResponse]:
        """Get sensor alerts."""
        try:
            return self.repository.get_sensor_alerts(
                farm_id=farm_id,
                status=status,
                device_type=device_type,
                device_id=device_id,
                measurement_type=measurement_type,
                alert_type=alert_type,
                location=location,
                substrate_batch_id=substrate_batch_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting sensor alerts: {e}")
            return []
    
    def update_alert_status(self, alert_id: str, update_data: SensorAlertUpdate) -> bool:
        """Update the status of a sensor alert."""
        try:
            return self.repository.update_alert_status(
                alert_id=alert_id,
                status=update_data.status,
                metadata=update_data.metadata
            )
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
            return False
    
    def get_active_alerts_count(self, farm_id: str) -> Dict[str, int]:
        """Get count of active alerts by type."""
        try:
            # Get active alerts
            alerts = self.repository.get_sensor_alerts(
                farm_id=farm_id,
                status="active"
            )
            
            # Count by alert type
            counts = {}
            for alert in alerts:
                key = f"{alert.measurement_type}_{alert.alert_type}"
                if key not in counts:
                    counts[key] = 0
                counts[key] += 1
            
            return counts
        except Exception as e:
            logger.error(f"Error getting active alerts count: {e}")
            return {}
    
    # Sensor Threshold Operations
    
    def create_sensor_threshold(self, threshold_data: SensorThresholdCreate) -> Optional[SensorThresholdResponse]:
        """Create a new sensor threshold."""
        try:
            # Create threshold
            threshold = SensorThreshold(
                farm_id=threshold_data.farm_id,
                device_type=threshold_data.device_type,
                measurement_type=threshold_data.measurement_type,
                high_threshold=threshold_data.high_threshold,
                low_threshold=threshold_data.low_threshold,
                unit=threshold_data.unit,
                location=threshold_data.location,
                substrate_batch_id=threshold_data.substrate_batch_id
            )
            
            # Save threshold
            success = self.repository.save_sensor_threshold(threshold)
            if not success:
                logger.error("Failed to save sensor threshold")
                return None
            
            # Return threshold response
            return SensorThresholdResponse(
                id=threshold.id,
                farm_id=threshold.farm_id,
                device_type=threshold.device_type,
                measurement_type=threshold.measurement_type,
                high_threshold=threshold.high_threshold,
                low_threshold=threshold.low_threshold,
                unit=threshold.unit,
                location=threshold.location,
                substrate_batch_id=threshold.substrate_batch_id,
                created_at=threshold.created_at,
                updated_at=threshold.updated_at
            )
        except Exception as e:
            logger.error(f"Error creating sensor threshold: {e}")
            return None
    
    def get_sensor_thresholds(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        measurement_type: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None
    ) -> List[SensorThresholdResponse]:
        """Get sensor thresholds."""
        try:
            return self.repository.get_sensor_thresholds(
                farm_id=farm_id,
                device_type=device_type,
                measurement_type=measurement_type,
                location=location,
                substrate_batch_id=substrate_batch_id
            )
        except Exception as e:
            logger.error(f"Error getting sensor thresholds: {e}")
            return []
    
    def update_sensor_threshold(
        self, 
        farm_id: str, 
        device_type: str,
        measurement_type: str,
        update_data: SensorThresholdUpdate,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None
    ) -> bool:
        """Update a sensor threshold."""
        try:
            # Get current thresholds
            thresholds = self.repository.get_sensor_thresholds(
                farm_id=farm_id,
                device_type=device_type,
                measurement_type=measurement_type,
                location=location,
                substrate_batch_id=substrate_batch_id
            )
            
            if not thresholds:
                logger.error(f"Threshold not found for update: {device_type}/{measurement_type}")
                return False
            
            threshold = thresholds[0]
            
            # Update fields
            if update_data.high_threshold is not None:
                threshold.high_threshold = update_data.high_threshold
            if update_data.low_threshold is not None:
                threshold.low_threshold = update_data.low_threshold
            if update_data.unit is not None:
                threshold.unit = update_data.unit
            if update_data.location is not None:
                threshold.location = update_data.location
            if update_data.substrate_batch_id is not None:
                threshold.substrate_batch_id = update_data.substrate_batch_id
            
            # Update timestamp
            threshold.updated_at = datetime.utcnow()
            
            # Save threshold
            return self.repository.save_sensor_threshold(SensorThreshold(**threshold.dict()))
        except Exception as e:
            logger.error(f"Error updating sensor threshold: {e}")
            return False
    
    # MQTT Message Processing
    
    def process_mqtt_message(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Process an MQTT message and save sensor reading."""
        try:
            # Parse topic
            # Expected format: bsf/{farm_id}/{device_type}/{device_id}
            parts = topic.split('/')
            if len(parts) != 4:
                logger.error(f"Invalid MQTT topic format: {topic}")
                return False
            
            farm_id = parts[1]
            device_type = parts[2]
            device_id = parts[3]
            
            # Extract reading data
            if "readings" not in payload:
                logger.error(f"Missing 'readings' in MQTT payload: {payload}")
                return False
            
            readings = payload["readings"]
            if not isinstance(readings, list):
                logger.error(f"'readings' is not a list in MQTT payload: {payload}")
                return False
            
            # Process each reading
            success = True
            for reading_data in readings:
                if not isinstance(reading_data, dict):
                    logger.error(f"Reading is not a dictionary: {reading_data}")
                    success = False
                    continue
                
                # Extract required fields
                measurement_type = reading_data.get("type")
                value = reading_data.get("value")
                unit = reading_data.get("unit")
                
                if not all([measurement_type, value is not None, unit]):
                    logger.error(f"Missing required fields in reading: {reading_data}")
                    success = False
                    continue
                
                # Type assertions after validation
                assert measurement_type is not None
                assert unit is not None
                assert value is not None
                
                # Extract optional fields
                location = reading_data.get("location")
                substrate_batch_id = reading_data.get("substrate_batch_id")
                metadata = reading_data.get("metadata")
                
                # Create reading
                reading = SensorReadingCreate(
                    farm_id=farm_id,
                    device_id=device_id,
                    device_type=device_type,
                    measurement_type=measurement_type,
                    value=float(value),
                    unit=unit,
                    location=location,
                    substrate_batch_id=substrate_batch_id,
                    metadata=metadata
                )
                
                # Save reading
                result = self.create_sensor_reading(reading)
                if not result:
                    logger.error(f"Failed to save reading: {reading}")
                    success = False
                else:
                    # Trigger anomaly detection
                    try:
                        from src.analytics.anomaly_detector import anomaly_detector
                        import asyncio
                        
                        # Create task for anomaly evaluation (non-blocking)
                        # Convert response to SensorReading for anomaly detection
                        reading_for_anomaly = SensorReading(
                            id=result.id,
                            farm_id=result.farm_id,
                            device_id=result.device_id,
                            device_type=result.device_type,
                            measurement_type=result.measurement_type,
                            value=result.value,
                            unit=result.unit,
                            timestamp=result.timestamp,
                            location=result.location,
                            substrate_batch_id=result.substrate_batch_id,
                            metadata=result.metadata
                        )
                        asyncio.create_task(anomaly_detector.evaluate_reading(reading_for_anomaly))
                    except Exception as e:
                        logger.error(f"Error triggering anomaly detection: {e}")
                        # Don't fail the whole process if anomaly detection fails
            
            return success
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
            return False
