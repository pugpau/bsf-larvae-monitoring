"""
InfluxDB client module for BSF Larvae Monitoring System.
This module handles connections and operations with InfluxDB.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from influxdb_client import InfluxDBClient as InfluxClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
from config import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InfluxDBClient:
    """Client for interacting with InfluxDB."""
    
    def __init__(self):
        """Initialize the InfluxDB client with settings from config."""
        self.url = settings.INFLUXDB_URL
        self.token = settings.INFLUXDB_TOKEN
        self.org = settings.INFLUXDB_ORG
        self.bucket = settings.INFLUXDB_BUCKET
        self.client = None
        self.write_api = None
        self.query_api = None
        
    def connect(self) -> bool:
        """
        Connect to InfluxDB server.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            self.client = InfluxClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            # Test connection by getting health status
            health = self.client.health()
            if health.status == "pass":
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                logger.info(f"Successfully connected to InfluxDB at {self.url}")
                return True
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False
    
    def close(self):
        """Close the InfluxDB client connection."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def write_sensor_data(data: Dict[str, Any]) -> bool:
    """
    Write sensor data to InfluxDB.
    
    Args:
        data: Dictionary containing sensor data with the following structure:
            {
                "farm_id": str,
                "device_id": str,
                "device_type": str,
                "timestamp": datetime (optional, defaults to current time),
                "measurements": {
                    "temperature": float,
                    "humidity": float,
                    "pressure": float,
                    "h2s": float,
                    "nh3": float,
                    # Other measurements as needed
                }
            }
    
    Returns:
        bool: True if write is successful, False otherwise.
    """
    try:
        with InfluxDBClient() as client:
            if not client.write_api:
                logger.error("InfluxDB client not properly initialized")
                return False
            
            # Extract data fields
            farm_id = data.get("farm_id")
            device_id = data.get("device_id")
            device_type = data.get("device_type")
            timestamp = data.get("timestamp", datetime.utcnow())
            measurements = data.get("measurements", {})
            
            # Validate required fields
            if not all([farm_id, device_id, device_type, measurements]):
                logger.error("Missing required fields in sensor data")
                return False
            
            # Prepare point data
            point = {
                "measurement": "sensor_data",
                "tags": {
                    "farm_id": farm_id,
                    "device_id": device_id,
                    "device_type": device_type
                },
                "time": timestamp,
                "fields": measurements
            }
            
            # Write to InfluxDB
            client.write_api.write(
                bucket=client.bucket,
                record=point
            )
            
            logger.info(f"Successfully wrote sensor data for device {device_id} to InfluxDB")
            return True
            
    except InfluxDBError as e:
        logger.error(f"InfluxDB error writing sensor data: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing sensor data: {e}")
        return False


def query_sensor_data(
    farm_id: Optional[str] = None,
    device_id: Optional[str] = None,
    device_type: Optional[str] = None,
    start_time: Optional[Union[datetime, str]] = None,
    end_time: Optional[Union[datetime, str]] = None,
    measurement_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query sensor data from InfluxDB with optional filters.
    
    Args:
        farm_id: Filter by farm ID
        device_id: Filter by device ID
        device_type: Filter by device type
        start_time: Start time for query range
        end_time: End time for query range
        measurement_type: Specific measurement to query (e.g., "temperature")
    
    Returns:
        List of dictionaries containing query results
    """
    try:
        with InfluxDBClient() as client:
            if not client.query_api:
                logger.error("InfluxDB client not properly initialized")
                return []
            
            # Build Flux query
            query = f'from(bucket: "{client.bucket}")'
            query += f' |> range(start: {start_time if start_time else "-1d"}, stop: {end_time if end_time else "now()"})'
            query += ' |> filter(fn: (r) => r._measurement == "sensor_data")'
            
            # Add optional filters
            if farm_id:
                query += f' |> filter(fn: (r) => r.farm_id == "{farm_id}")'
            if device_id:
                query += f' |> filter(fn: (r) => r.device_id == "{device_id}")'
            if device_type:
                query += f' |> filter(fn: (r) => r.device_type == "{device_type}")'
            if measurement_type:
                query += f' |> filter(fn: (r) => r._field == "{measurement_type}")'
            
            # Execute query
            result = client.query_api.query(query=query, org=client.org)
            
            # Process results
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "time": record.get_time(),
                        "farm_id": record.values.get("farm_id"),
                        "device_id": record.values.get("device_id"),
                        "device_type": record.values.get("device_type"),
                        "field": record.get_field(),
                        "value": record.get_value()
                    })
            
            logger.info(f"Successfully queried sensor data, returned {len(data)} records")
            return data
            
    except InfluxDBError as e:
        logger.error(f"InfluxDB error querying sensor data: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying sensor data: {e}")
        return []


# Singleton instance for global use
influxdb_client = InfluxDBClient()
