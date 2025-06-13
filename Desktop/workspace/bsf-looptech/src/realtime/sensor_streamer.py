"""
Real-time sensor data streaming service.
Integrates MQTT sensor data with WebSocket broadcasting for live dashboard updates.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from src.websocket.manager import websocket_manager, WebSocketMessage, MessageType
from src.database.influxdb import InfluxDBClient
from src.sensors.repository import SensorRepository
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SensorDataPoint:
    """Structured sensor data point."""
    farm_id: str
    device_id: str
    device_type: str
    measurement_type: str
    value: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None
    substrate_batch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RealTimeSensorStreamer:
    """Service for streaming real-time sensor data via WebSocket."""
    
    def __init__(self):
        self.influxdb = None
        self.sensor_repository = SensorRepository()
        self.is_running = False
        self.streaming_tasks = []
        
        # Streaming configuration
        self.batch_size = 10
        self.stream_interval = 1.0  # seconds
        self.buffer = []
        
        # Statistics
        self.stats = {
            "messages_processed": 0,
            "messages_streamed": 0,
            "errors": 0,
            "start_time": None
        }
    
    async def start_streaming(self):
        """Start the real-time streaming service."""
        if self.is_running:
            logger.warning("Sensor streaming is already running")
            return
        
        try:
            self.is_running = True
            self.stats["start_time"] = datetime.utcnow()
            
            # Start background tasks
            self.streaming_tasks = [
                asyncio.create_task(self._stream_recent_data()),
                asyncio.create_task(self._process_data_buffer()),
                asyncio.create_task(self._monitor_device_status())
            ]
            
            logger.info("Real-time sensor streaming started")
            
        except Exception as e:
            logger.error(f"Failed to start sensor streaming: {e}")
            self.is_running = False
            raise
    
    async def stop_streaming(self):
        """Stop the real-time streaming service."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # Cancel all tasks
            for task in self.streaming_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.streaming_tasks, return_exceptions=True)
            self.streaming_tasks.clear()
            
            logger.info("Real-time sensor streaming stopped")
            
        except Exception as e:
            logger.error(f"Error stopping sensor streaming: {e}")
    
    async def process_mqtt_message(self, topic: str, payload: Dict[str, Any]):
        """
        Process incoming MQTT sensor data and stream to WebSocket clients.
        
        Args:
            topic: MQTT topic (e.g., "bsf/farm123/gas_sensor/device001")
            payload: Sensor data payload
        """
        try:
            # Parse topic to extract farm_id, device_type, device_id
            topic_parts = topic.split('/')
            if len(topic_parts) != 4 or topic_parts[0] != 'bsf':
                logger.warning(f"Invalid MQTT topic format: {topic}")
                return
            
            farm_id = topic_parts[1]
            device_type = topic_parts[2]
            device_id = topic_parts[3]
            
            # Process sensor readings from payload
            readings = payload.get('readings', [])
            timestamp = datetime.fromisoformat(payload.get('timestamp', datetime.utcnow().isoformat()))
            
            sensor_data_points = []
            
            for reading in readings:
                data_point = SensorDataPoint(
                    farm_id=farm_id,
                    device_id=device_id,
                    device_type=device_type,
                    measurement_type=reading.get('type'),
                    value=float(reading.get('value', 0)),
                    unit=reading.get('unit', ''),
                    timestamp=timestamp,
                    location=payload.get('location'),
                    substrate_batch_id=payload.get('substrate_batch_id'),
                    metadata=payload.get('metadata')
                )
                sensor_data_points.append(data_point)
            
            # Add to buffer for processing
            self.buffer.extend(sensor_data_points)
            self.stats["messages_processed"] += len(sensor_data_points)
            
            # Immediate streaming for critical measurements
            await self._stream_critical_data(sensor_data_points)
            
        except Exception as e:
            logger.error(f"Error processing MQTT message from topic {topic}: {e}")
            self.stats["errors"] += 1
    
    async def _stream_critical_data(self, data_points: list[SensorDataPoint]):
        """Stream critical sensor data immediately."""
        critical_measurements = ['h2s', 'nh3', 'temperature']
        
        for data_point in data_points:
            if data_point.measurement_type in critical_measurements:
                await self._stream_sensor_data(data_point)
    
    async def _stream_sensor_data(self, data_point: SensorDataPoint):
        """Stream individual sensor data point to WebSocket clients."""
        try:
            # Create WebSocket message
            message_data = {
                "farm_id": data_point.farm_id,
                "device_id": data_point.device_id,
                "device_type": data_point.device_type,
                "measurement_type": data_point.measurement_type,
                "value": data_point.value,
                "unit": data_point.unit,
                "timestamp": data_point.timestamp.isoformat(),
                "location": data_point.location,
                "substrate_batch_id": data_point.substrate_batch_id,
                "metadata": data_point.metadata
            }
            
            message = WebSocketMessage(
                message_type=MessageType.SENSOR_DATA,
                data=message_data,
                farm_id=data_point.farm_id,
                device_id=data_point.device_id
            )
            
            # Broadcast to interested clients
            await websocket_manager.broadcast_to_farm(data_point.farm_id, message)
            await websocket_manager.broadcast_to_device(data_point.device_id, message)
            
            self.stats["messages_streamed"] += 1
            
            logger.debug(f"Streamed sensor data: {data_point.device_id}/{data_point.measurement_type} = {data_point.value}")
            
        except Exception as e:
            logger.error(f"Error streaming sensor data: {e}")
            self.stats["errors"] += 1
    
    async def _process_data_buffer(self):
        """Process buffered sensor data in batches."""
        while self.is_running:
            try:
                if len(self.buffer) >= self.batch_size:
                    # Process batch
                    batch = self.buffer[:self.batch_size]
                    self.buffer = self.buffer[self.batch_size:]
                    
                    # Stream batch data
                    for data_point in batch:
                        await self._stream_sensor_data(data_point)
                
                await asyncio.sleep(self.stream_interval)
                
            except Exception as e:
                logger.error(f"Error processing data buffer: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(5)  # Back off on error
    
    async def _stream_recent_data(self):
        """Stream recent sensor data for new WebSocket connections."""
        while self.is_running:
            try:
                # This could query recent data from InfluxDB and stream to new connections
                # For now, we'll just monitor and log
                await asyncio.sleep(30)  # Check every 30 seconds
                
                logger.debug(f"Streaming stats: {self.get_stats()}")
                
            except Exception as e:
                logger.error(f"Error in recent data streaming: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_device_status(self):
        """Monitor device status and stream updates."""
        device_last_seen = {}
        
        while self.is_running:
            try:
                # Check for devices that haven't sent data recently
                current_time = datetime.utcnow()
                offline_threshold = 300  # 5 minutes
                
                # This would typically query device status from the database
                # For now, we'll simulate device status monitoring
                
                # Stream device status updates
                for farm_id in websocket_manager.farm_rooms.keys():
                    status_message = WebSocketMessage(
                        message_type=MessageType.DEVICE_STATUS,
                        data={
                            "farm_id": farm_id,
                            "online_devices": 5,  # Placeholder
                            "offline_devices": 1,  # Placeholder
                            "total_devices": 6,
                            "last_update": current_time.isoformat()
                        },
                        farm_id=farm_id
                    )
                    
                    await websocket_manager.broadcast_to_farm(farm_id, status_message)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring device status: {e}")
                await asyncio.sleep(30)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        
        return {
            **self.stats,
            "is_running": self.is_running,
            "buffer_size": len(self.buffer),
            "uptime_seconds": uptime,
            "active_tasks": len(self.streaming_tasks)
        }


# Global sensor streamer instance
sensor_streamer = RealTimeSensorStreamer()