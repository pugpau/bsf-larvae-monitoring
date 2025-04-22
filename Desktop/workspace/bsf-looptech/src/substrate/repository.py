"""
Repository for substrate data storage and retrieval.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from influxdb_client import Point
from database.influxdb import InfluxDBClient
from substrate.models import SubstrateType, SubstrateBatch, SubstrateChangeLog
from config import settings

logger = logging.getLogger(__name__)

class SubstrateRepository:
    """Repository for substrate data storage and retrieval using InfluxDB."""
    
    def __init__(self):
        self.bucket = settings.INFLUXDB_BUCKET
    
    def save_substrate_type(self, substrate_type: SubstrateType) -> bool:
        """Save a substrate type to the database."""
        try:
            with InfluxDBClient() as client:
                if not client.write_api:
                    logger.error("InfluxDB client not properly initialized")
                    return False
                
                point = Point("substrate_type") \
                    .tag("id", substrate_type.id) \
                    .tag("type", substrate_type.type.value) \
                    .field("name", substrate_type.name) \
                    .field("description", substrate_type.description or "") \
                    .field("attributes", substrate_type.json()) \
                    .time(substrate_type.updated_at)
                
                client.write_api.write(bucket=self.bucket, record=point)
                logger.info(f"Saved substrate type {substrate_type.id}")
                return True
        except Exception as e:
            logger.error(f"Error saving substrate type: {e}")
            return False
    
    def get_substrate_type(self, substrate_type_id: str) -> Optional[SubstrateType]:
        """Retrieve a substrate type by ID."""
        try:
            with InfluxDBClient() as client:
                if not client.query_api:
                    return None
                
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: 0)
                    |> filter(fn: (r) => r._measurement == "substrate_type")
                    |> filter(fn: (r) => r.id == "{substrate_type_id}")
                    |> last()
                '''
                
                result = client.query_api.query(query=query, org=client.org)
                
                if not result or len(result) == 0:
                    return None
                
                for table in result:
                    for record in table.records:
                        if record.get_field() == "attributes":
                            return SubstrateType.parse_raw(record.get_value())
                
                return None
        except Exception as e:
            logger.error(f"Error retrieving substrate type: {e}")
            return None
    
    def get_all_substrate_types(self) -> List[SubstrateType]:
        """Retrieve all substrate types."""
        try:
            with InfluxDBClient() as client:
                if not client.query_api:
                    return []
                
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: 0)
                    |> filter(fn: (r) => r._measurement == "substrate_type")
                    |> filter(fn: (r) => r._field == "attributes")
                    |> group(columns: ["id"])
                    |> last()
                '''
                
                result = client.query_api.query(query=query, org=client.org)
                
                substrate_types = []
                for table in result:
                    for record in table.records:
                        substrate_types.append(SubstrateType.parse_raw(record.get_value()))
                
                return substrate_types
        except Exception as e:
            logger.error(f"Error retrieving all substrate types: {e}")
            return []
    
    def save_substrate_batch(self, batch: SubstrateBatch) -> bool:
        """Save a substrate batch to the database."""
        try:
            with InfluxDBClient() as client:
                if not client.write_api:
                    return False
                
                point = Point("substrate_batch") \
                    .tag("id", batch.id) \
                    .tag("farm_id", batch.farm_id) \
                    .tag("status", batch.status) \
                    .field("name", batch.name or "") \
                    .field("description", batch.description or "") \
                    .field("batch_data", batch.json()) \
                    .time(batch.updated_at)
                
                client.write_api.write(bucket=self.bucket, record=point)
                logger.info(f"Saved substrate batch {batch.id}")
                return True
        except Exception as e:
            logger.error(f"Error saving substrate batch: {e}")
            return False
    
    def get_substrate_batch(self, batch_id: str) -> Optional[SubstrateBatch]:
        """Retrieve a substrate batch by ID."""
        try:
            with InfluxDBClient() as client:
                if not client.query_api:
                    return None
                
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: 0)
                    |> filter(fn: (r) => r._measurement == "substrate_batch")
                    |> filter(fn: (r) => r.id == "{batch_id}")
                    |> filter(fn: (r) => r._field == "batch_data")
                    |> last()
                '''
                
                result = client.query_api.query(query=query, org=client.org)
                
                if not result or len(result) == 0:
                    return None
                
                for table in result:
                    for record in table.records:
                        return SubstrateBatch.parse_raw(record.get_value())
                
                return None
        except Exception as e:
            logger.error(f"Error retrieving substrate batch: {e}")
            return None
    
    def get_substrate_batches_by_farm(self, farm_id: str, status: Optional[str] = None) -> List[SubstrateBatch]:
        """Retrieve substrate batches for a specific farm."""
        try:
            with InfluxDBClient() as client:
                if not client.query_api:
                    return []
                
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: 0)
                    |> filter(fn: (r) => r._measurement == "substrate_batch")
                    |> filter(fn: (r) => r.farm_id == "{farm_id}")
                '''
                
                if status:
                    query += f'\n    |> filter(fn: (r) => r.status == "{status}")'
                
                query += '''
                    |> filter(fn: (r) => r._field == "batch_data")
                    |> group(columns: ["id"])
                    |> last()
                '''
                
                result = client.query_api.query(query=query, org=client.org)
                
                batches = []
                for table in result:
                    for record in table.records:
                        batches.append(SubstrateBatch.parse_raw(record.get_value()))
                
                return batches
        except Exception as e:
            logger.error(f"Error retrieving substrate batches: {e}")
            return []
    
    def save_substrate_change_log(self, change_log: SubstrateChangeLog) -> bool:
        """Save a substrate change log entry."""
        try:
            with InfluxDBClient() as client:
                if not client.write_api:
                    return False
                
                point = Point("substrate_change_log") \
                    .tag("id", change_log.id) \
                    .tag("batch_id", change_log.batch_id) \
                    .tag("change_type", change_log.change_type) \
                    .field("changed_by", change_log.changed_by or "") \
                    .field("change_reason", change_log.change_reason or "") \
                    .field("log_data", change_log.json()) \
                    .time(change_log.timestamp)
                
                client.write_api.write(bucket=self.bucket, record=point)
                logger.info(f"Saved substrate change log {change_log.id}")
                return True
        except Exception as e:
            logger.error(f"Error saving substrate change log: {e}")
            return False
    
    def get_change_logs_for_batch(self, batch_id: str) -> List[SubstrateChangeLog]:
        """Retrieve change logs for a specific substrate batch."""
        try:
            with InfluxDBClient() as client:
                if not client.query_api:
                    return []
                
                query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: 0)
                    |> filter(fn: (r) => r._measurement == "substrate_change_log")
                    |> filter(fn: (r) => r.batch_id == "{batch_id}")
                    |> filter(fn: (r) => r._field == "log_data")
                    |> sort(columns: ["_time"], desc: false)
                '''
                
                result = client.query_api.query(query=query, org=client.org)
                
                logs = []
                for table in result:
                    for record in table.records:
                        logs.append(SubstrateChangeLog.parse_raw(record.get_value()))
                
                return logs
        except Exception as e:
            logger.error(f"Error retrieving change logs: {e}")
            return []
