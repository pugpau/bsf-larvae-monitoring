"""
Repository for sensor data management.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.database.influxdb import InfluxDBClient
from src.sensors.models import (
    SensorReading, SensorDevice, SensorAlert, SensorThreshold,
    SensorReadingResponse, SensorDeviceResponse, SensorAlertResponse, SensorThresholdResponse
)

logger = logging.getLogger(__name__)

class SensorRepository:
    """Repository for sensor data management."""
    
    def __init__(self):
        self.influxdb = InfluxDBClient()
    
    # Sensor Reading Operations
    
    def save_sensor_reading(self, reading: SensorReading) -> bool:
        """Save a sensor reading to InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return False
            
            # Prepare data point
            point = {
                "measurement": "sensor_readings",
                "tags": {
                    "farm_id": reading.farm_id,
                    "device_id": reading.device_id,
                    "device_type": reading.device_type,
                    "measurement_type": reading.measurement_type,
                    "unit": reading.unit
                },
                "fields": {
                    "value": reading.value,
                    "reading_id": reading.id
                },
                "time": reading.timestamp.isoformat()
            }
            
            # Add optional tags
            if reading.location:
                point["tags"]["location"] = reading.location
            if reading.substrate_batch_id:
                point["tags"]["substrate_batch_id"] = reading.substrate_batch_id
            
            # Add metadata as fields if present
            if reading.metadata:
                for key, value in reading.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        point["fields"][f"metadata_{key}"] = value
            
            # Write to InfluxDB
            success = self.influxdb.write_point(point)
            if success:
                logger.info(f"Saved sensor reading: {reading.id}")
                
                # Update last_seen timestamp for the device
                self._update_device_last_seen(reading.farm_id, reading.device_id, reading.timestamp)
                
                # Check thresholds and create alerts if needed
                self._check_thresholds(reading)
                
                return True
            else:
                logger.error(f"Failed to save sensor reading: {reading.id}")
                return False
        except Exception as e:
            logger.error(f"Error saving sensor reading: {e}")
            return False
        finally:
            self.influxdb.close()
    
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
        """Get sensor readings from InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return []
            
            # Build query
            query = f'from(bucket:"{self.influxdb.bucket}") |> range('
            
            # Add time range
            if start_time and end_time:
                query += f'start: {start_time.isoformat()}, stop: {end_time.isoformat()}'
            elif start_time:
                query += f'start: {start_time.isoformat()}'
            elif end_time:
                query += f'stop: {end_time.isoformat()}'
            else:
                # Default to last 24 hours
                query += f'start: -24h'
            
            query += f') |> filter(fn: (r) => r._measurement == "sensor_readings")'
            query += f' |> filter(fn: (r) => r.farm_id == "{farm_id}")'
            
            # Add optional filters
            if device_type:
                query += f' |> filter(fn: (r) => r.device_type == "{device_type}")'
            if device_id:
                query += f' |> filter(fn: (r) => r.device_id == "{device_id}")'
            if measurement_type:
                query += f' |> filter(fn: (r) => r.measurement_type == "{measurement_type}")'
            if location:
                query += f' |> filter(fn: (r) => r.location == "{location}")'
            if substrate_batch_id:
                query += f' |> filter(fn: (r) => r.substrate_batch_id == "{substrate_batch_id}")'
            
            # Sort and limit
            query += f' |> sort(columns: ["_time"], desc: true) |> limit(n: {limit})'
            
            # Execute query
            results = self.influxdb.query(query)
            
            # Process results
            readings = []
            for table in results:
                for record in table.records:
                    # Extract fields and tags
                    reading_id = record.values.get("reading_id", "")
                    farm_id = record.values.get("farm_id", "")
                    device_id = record.values.get("device_id", "")
                    device_type = record.values.get("device_type", "")
                    measurement_type = record.values.get("measurement_type", "")
                    value = record.values.get("_value", 0.0)
                    unit = record.values.get("unit", "")
                    timestamp = record.values.get("_time", datetime.utcnow())
                    location = record.values.get("location", None)
                    substrate_batch_id = record.values.get("substrate_batch_id", None)
                    
                    # Extract metadata
                    metadata = {}
                    for key, value in record.values.items():
                        if key.startswith("metadata_"):
                            metadata_key = key.replace("metadata_", "")
                            metadata[metadata_key] = value
                    
                    # Create reading response
                    reading = SensorReadingResponse(
                        id=reading_id,
                        farm_id=farm_id,
                        device_id=device_id,
                        device_type=device_type,
                        timestamp=timestamp,
                        measurement_type=measurement_type,
                        value=value,
                        unit=unit,
                        location=location,
                        substrate_batch_id=substrate_batch_id,
                        metadata=metadata if metadata else None
                    )
                    readings.append(reading)
            
            return readings
        except Exception as e:
            logger.error(f"Error getting sensor readings: {e}")
            return []
        finally:
            self.influxdb.close()
    
    # Sensor Device Operations
    
    def save_sensor_device(self, device: SensorDevice) -> bool:
        """Save a sensor device to InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return False
            
            # Prepare data point
            point = {
                "measurement": "sensor_devices",
                "tags": {
                    "farm_id": device.farm_id,
                    "device_id": device.device_id,
                    "device_type": device.device_type,
                    "status": device.status
                },
                "fields": {
                    "device_uuid": device.id,
                    "name": device.name or "",
                    "description": device.description or "",
                    "created_at": device.created_at.isoformat(),
                    "updated_at": device.updated_at.isoformat()
                },
                "time": device.updated_at.isoformat()
            }
            
            # Add optional tags
            if device.location:
                point["tags"]["location"] = device.location
            
            # Add last_seen if present
            if device.last_seen:
                point["fields"]["last_seen"] = device.last_seen.isoformat()
            
            # Add metadata as fields if present
            if device.metadata:
                for key, value in device.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        point["fields"][f"metadata_{key}"] = value
            
            # Write to InfluxDB
            success = self.influxdb.write_point(point)
            if success:
                logger.info(f"Saved sensor device: {device.id}")
                return True
            else:
                logger.error(f"Failed to save sensor device: {device.id}")
                return False
        except Exception as e:
            logger.error(f"Error saving sensor device: {e}")
            return False
        finally:
            self.influxdb.close()
    
    def get_sensor_devices(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[SensorDeviceResponse]:
        """Get sensor devices from InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return []
            
            # Build query
            query = f'from(bucket:"{self.influxdb.bucket}") |> range(start: -30d)'
            query += f' |> filter(fn: (r) => r._measurement == "sensor_devices")'
            query += f' |> filter(fn: (r) => r.farm_id == "{farm_id}")'
            
            # Add optional filters
            if device_type:
                query += f' |> filter(fn: (r) => r.device_type == "{device_type}")'
            if device_id:
                query += f' |> filter(fn: (r) => r.device_id == "{device_id}")'
            if status:
                query += f' |> filter(fn: (r) => r.status == "{status}")'
            if location:
                query += f' |> filter(fn: (r) => r.location == "{location}")'
            
            # Group by device and get latest record
            query += f' |> group(columns: ["device_id"]) |> sort(columns: ["_time"], desc: true) |> limit(n: 1)'
            
            # Execute query
            results = self.influxdb.query(query)
            
            # Process results
            devices = []
            for table in results:
                for record in table.records:
                    # Extract fields and tags
                    device_id = record.values.get("device_id", "")
                    device_uuid = record.values.get("device_uuid", "")
                    farm_id = record.values.get("farm_id", "")
                    device_type = record.values.get("device_type", "")
                    name = record.values.get("name", "")
                    description = record.values.get("description", "")
                    status = record.values.get("status", "active")
                    location = record.values.get("location", None)
                    created_at_str = record.values.get("created_at", "")
                    updated_at_str = record.values.get("updated_at", "")
                    last_seen_str = record.values.get("last_seen", None)
                    
                    # Parse datetime strings
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                    updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.utcnow()
                    last_seen = datetime.fromisoformat(last_seen_str) if last_seen_str else None
                    
                    # Extract metadata
                    metadata = {}
                    for key, value in record.values.items():
                        if key.startswith("metadata_"):
                            metadata_key = key.replace("metadata_", "")
                            metadata[metadata_key] = value
                    
                    # Create device response
                    device = SensorDeviceResponse(
                        id=device_uuid,
                        farm_id=farm_id,
                        device_id=device_id,
                        device_type=device_type,
                        name=name if name else None,
                        description=description if description else None,
                        location=location,
                        status=status,
                        last_seen=last_seen,
                        metadata=metadata if metadata else None,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    devices.append(device)
            
            return devices
        except Exception as e:
            logger.error(f"Error getting sensor devices: {e}")
            return []
        finally:
            self.influxdb.close()
    
    def _update_device_last_seen(self, farm_id: str, device_id: str, timestamp: datetime) -> bool:
        """Update the last_seen timestamp for a device."""
        try:
            # Get the device
            devices = self.get_sensor_devices(farm_id=farm_id, device_id=device_id)
            if not devices:
                logger.warning(f"Device not found for update: {device_id}")
                return False
            
            device = devices[0]
            
            # Update last_seen
            device.last_seen = timestamp
            device.updated_at = datetime.utcnow()
            
            # Save the device
            return self.save_sensor_device(SensorDevice(**device.dict()))
        except Exception as e:
            logger.error(f"Error updating device last_seen: {e}")
            return False
    
    # Sensor Alert Operations
    
    def save_sensor_alert(self, alert: SensorAlert) -> bool:
        """Save a sensor alert to InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return False
            
            # Prepare data point
            point = {
                "measurement": "sensor_alerts",
                "tags": {
                    "farm_id": alert.farm_id,
                    "device_id": alert.device_id,
                    "device_type": alert.device_type,
                    "measurement_type": alert.measurement_type,
                    "alert_type": alert.alert_type,
                    "status": alert.status,
                    "unit": alert.unit
                },
                "fields": {
                    "alert_id": alert.id,
                    "threshold": alert.threshold,
                    "actual_value": alert.actual_value
                },
                "time": alert.timestamp.isoformat()
            }
            
            # Add optional tags
            if alert.location:
                point["tags"]["location"] = alert.location
            if alert.substrate_batch_id:
                point["tags"]["substrate_batch_id"] = alert.substrate_batch_id
            
            # Add metadata as fields if present
            if alert.metadata:
                for key, value in alert.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        point["fields"][f"metadata_{key}"] = value
            
            # Write to InfluxDB
            success = self.influxdb.write_point(point)
            if success:
                logger.info(f"Saved sensor alert: {alert.id}")
                return True
            else:
                logger.error(f"Failed to save sensor alert: {alert.id}")
                return False
        except Exception as e:
            logger.error(f"Error saving sensor alert: {e}")
            return False
        finally:
            self.influxdb.close()
    
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
        """Get sensor alerts from InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return []
            
            # Build query
            query = f'from(bucket:"{self.influxdb.bucket}") |> range('
            
            # Add time range
            if start_time and end_time:
                query += f'start: {start_time.isoformat()}, stop: {end_time.isoformat()}'
            elif start_time:
                query += f'start: {start_time.isoformat()}'
            elif end_time:
                query += f'stop: {end_time.isoformat()}'
            else:
                # Default to last 24 hours
                query += f'start: -24h'
            
            query += f') |> filter(fn: (r) => r._measurement == "sensor_alerts")'
            query += f' |> filter(fn: (r) => r.farm_id == "{farm_id}")'
            
            # Add optional filters
            if status:
                query += f' |> filter(fn: (r) => r.status == "{status}")'
            if device_type:
                query += f' |> filter(fn: (r) => r.device_type == "{device_type}")'
            if device_id:
                query += f' |> filter(fn: (r) => r.device_id == "{device_id}")'
            if measurement_type:
                query += f' |> filter(fn: (r) => r.measurement_type == "{measurement_type}")'
            if alert_type:
                query += f' |> filter(fn: (r) => r.alert_type == "{alert_type}")'
            if location:
                query += f' |> filter(fn: (r) => r.location == "{location}")'
            if substrate_batch_id:
                query += f' |> filter(fn: (r) => r.substrate_batch_id == "{substrate_batch_id}")'
            
            # Sort and limit
            query += f' |> sort(columns: ["_time"], desc: true) |> limit(n: {limit})'
            
            # Execute query
            results = self.influxdb.query(query)
            
            # Process results
            alerts = []
            for table in results:
                for record in table.records:
                    # Extract fields and tags
                    alert_id = record.values.get("alert_id", "")
                    farm_id = record.values.get("farm_id", "")
                    device_id = record.values.get("device_id", "")
                    device_type = record.values.get("device_type", "")
                    measurement_type = record.values.get("measurement_type", "")
                    alert_type = record.values.get("alert_type", "")
                    status = record.values.get("status", "active")
                    threshold = record.values.get("threshold", 0.0)
                    actual_value = record.values.get("actual_value", 0.0)
                    unit = record.values.get("unit", "")
                    timestamp = record.values.get("_time", datetime.utcnow())
                    location = record.values.get("location", None)
                    substrate_batch_id = record.values.get("substrate_batch_id", None)
                    
                    # Extract metadata
                    metadata = {}
                    for key, value in record.values.items():
                        if key.startswith("metadata_"):
                            metadata_key = key.replace("metadata_", "")
                            metadata[metadata_key] = value
                    
                    # Create alert response
                    alert = SensorAlertResponse(
                        id=alert_id,
                        farm_id=farm_id,
                        device_id=device_id,
                        device_type=device_type,
                        measurement_type=measurement_type,
                        alert_type=alert_type,
                        threshold=threshold,
                        actual_value=actual_value,
                        unit=unit,
                        timestamp=timestamp,
                        status=status,
                        location=location,
                        substrate_batch_id=substrate_batch_id,
                        metadata=metadata if metadata else None
                    )
                    alerts.append(alert)
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting sensor alerts: {e}")
            return []
        finally:
            self.influxdb.close()
    
    def update_alert_status(self, alert_id: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update the status of a sensor alert."""
        try:
            # Get all alerts with the given ID
            alerts = []
            for farm_id in self._get_all_farm_ids():
                farm_alerts = self.get_sensor_alerts(farm_id=farm_id)
                alerts.extend([a for a in farm_alerts if a.id == alert_id])
            
            if not alerts:
                logger.warning(f"Alert not found for update: {alert_id}")
                return False
            
            alert = alerts[0]
            
            # Update status and metadata
            alert.status = status
            if metadata:
                if alert.metadata:
                    alert.metadata.update(metadata)
                else:
                    alert.metadata = metadata
            
            # Save the alert
            return self.save_sensor_alert(SensorAlert(**alert.dict()))
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
            return False
    
    # Sensor Threshold Operations
    
    def save_sensor_threshold(self, threshold: SensorThreshold) -> bool:
        """Save a sensor threshold to InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return False
            
            # Prepare data point
            point = {
                "measurement": "sensor_thresholds",
                "tags": {
                    "farm_id": threshold.farm_id,
                    "device_type": threshold.device_type,
                    "measurement_type": threshold.measurement_type,
                    "unit": threshold.unit
                },
                "fields": {
                    "threshold_id": threshold.id,
                    "high_threshold": threshold.high_threshold if threshold.high_threshold is not None else float('inf'),
                    "low_threshold": threshold.low_threshold if threshold.low_threshold is not None else float('-inf'),
                    "created_at": threshold.created_at.isoformat(),
                    "updated_at": threshold.updated_at.isoformat()
                },
                "time": threshold.updated_at.isoformat()
            }
            
            # Add optional tags
            if threshold.location:
                point["tags"]["location"] = threshold.location
            if threshold.substrate_batch_id:
                point["tags"]["substrate_batch_id"] = threshold.substrate_batch_id
            
            # Write to InfluxDB
            success = self.influxdb.write_point(point)
            if success:
                logger.info(f"Saved sensor threshold: {threshold.id}")
                return True
            else:
                logger.error(f"Failed to save sensor threshold: {threshold.id}")
                return False
        except Exception as e:
            logger.error(f"Error saving sensor threshold: {e}")
            return False
        finally:
            self.influxdb.close()
    
    def get_sensor_thresholds(
        self, 
        farm_id: str, 
        device_type: Optional[str] = None,
        measurement_type: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None
    ) -> List[SensorThresholdResponse]:
        """Get sensor thresholds from InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return []
            
            # Build query
            query = f'from(bucket:"{self.influxdb.bucket}") |> range(start: -30d)'
            query += f' |> filter(fn: (r) => r._measurement == "sensor_thresholds")'
            query += f' |> filter(fn: (r) => r.farm_id == "{farm_id}")'
            
            # Add optional filters
            if device_type:
                query += f' |> filter(fn: (r) => r.device_type == "{device_type}")'
            if measurement_type:
                query += f' |> filter(fn: (r) => r.measurement_type == "{measurement_type}")'
            if location:
                query += f' |> filter(fn: (r) => r.location == "{location}")'
            if substrate_batch_id:
                query += f' |> filter(fn: (r) => r.substrate_batch_id == "{substrate_batch_id}")'
            
            # Group by threshold parameters and get latest record
            group_columns = ["farm_id", "device_type", "measurement_type"]
            if location:
                group_columns.append("location")
            if substrate_batch_id:
                group_columns.append("substrate_batch_id")
            
            query += f' |> group(columns: {group_columns}) |> sort(columns: ["_time"], desc: true) |> limit(n: 1)'
            
            # Execute query
            results = self.influxdb.query(query)
            
            # Process results
            thresholds = []
            for table in results:
                for record in table.records:
                    # Extract fields and tags
                    threshold_id = record.values.get("threshold_id", "")
                    farm_id = record.values.get("farm_id", "")
                    device_type = record.values.get("device_type", "")
                    measurement_type = record.values.get("measurement_type", "")
                    high_threshold = record.values.get("high_threshold", None)
                    low_threshold = record.values.get("low_threshold", None)
                    unit = record.values.get("unit", "")
                    location = record.values.get("location", None)
                    substrate_batch_id = record.values.get("substrate_batch_id", None)
                    created_at_str = record.values.get("created_at", "")
                    updated_at_str = record.values.get("updated_at", "")
                    
                    # Handle infinity values
                    if high_threshold == float('inf'):
                        high_threshold = None
                    if low_threshold == float('-inf'):
                        low_threshold = None
                    
                    # Parse datetime strings
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                    updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.utcnow()
                    
                    # Create threshold response
                    threshold = SensorThresholdResponse(
                        id=threshold_id,
                        farm_id=farm_id,
                        device_type=device_type,
                        measurement_type=measurement_type,
                        high_threshold=high_threshold,
                        low_threshold=low_threshold,
                        unit=unit,
                        location=location,
                        substrate_batch_id=substrate_batch_id,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    thresholds.append(threshold)
            
            return thresholds
        except Exception as e:
            logger.error(f"Error getting sensor thresholds: {e}")
            return []
        finally:
            self.influxdb.close()
    
    # Helper methods
    
    def _check_thresholds(self, reading: SensorReading) -> None:
        """Check if a sensor reading exceeds any thresholds and create alerts if needed."""
        try:
            # Get thresholds for this reading
            thresholds = self.get_sensor_thresholds(
                farm_id=reading.farm_id,
                device_type=reading.device_type,
                measurement_type=reading.measurement_type,
                location=reading.location,
                substrate_batch_id=reading.substrate_batch_id
            )
            
            if not thresholds:
                # No thresholds defined
                return
            
            # Check each threshold
            for threshold in thresholds:
                # Check high threshold
                if threshold.high_threshold is not None and reading.value > threshold.high_threshold:
                    # Create high alert
                    alert = SensorAlert(
                        farm_id=reading.farm_id,
                        device_id=reading.device_id,
                        device_type=reading.device_type,
                        measurement_type=reading.measurement_type,
                        alert_type="high",
                        threshold=threshold.high_threshold,
                        actual_value=reading.value,
                        unit=reading.unit,
                        location=reading.location,
                        substrate_batch_id=reading.substrate_batch_id,
                        metadata=reading.metadata
                    )
                    self.save_sensor_alert(alert)
                
                # Check low threshold
                if threshold.low_threshold is not None and reading.value < threshold.low_threshold:
                    # Create low alert
                    alert = SensorAlert(
                        farm_id=reading.farm_id,
                        device_id=reading.device_id,
                        device_type=reading.device_type,
                        measurement_type=reading.measurement_type,
                        alert_type="low",
                        threshold=threshold.low_threshold,
                        actual_value=reading.value,
                        unit=reading.unit,
                        location=reading.location,
                        substrate_batch_id=reading.substrate_batch_id,
                        metadata=reading.metadata
                    )
                    self.save_sensor_alert(alert)
        except Exception as e:
            logger.error(f"Error checking thresholds: {e}")
    
    def _get_all_farm_ids(self) -> List[str]:
        """Get all farm IDs from InfluxDB."""
        try:
            # Connect to InfluxDB
            if not self.influxdb.connect():
                logger.error("Failed to connect to InfluxDB")
                return []
            
            # Build query to get distinct farm_ids
            query = f'from(bucket:"{self.influxdb.bucket}") |> range(start: -30d)'
            query += f' |> filter(fn: (r) => r._measurement == "sensor_devices")'
            query += f' |> group(columns: ["farm_id"]) |> distinct(column: "farm_id")'
            
            # Execute query
            results = self.influxdb.query(query)
            
            # Process results
            farm_ids = []
            for table in results:
                for record in table.records:
                    farm_id = record.values.get("farm_id", "")
                    if farm_id and farm_id not in farm_ids:
                        farm_ids.append(farm_id)
            
            return farm_ids
        except Exception as e:
            logger.error(f"Error getting farm IDs: {e}")
            return []
        finally:
            self.influxdb.close()
