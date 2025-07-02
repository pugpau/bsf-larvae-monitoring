"""
Database module for BSF Larvae Monitoring System.
This module handles database connections and operations.
"""

from src.database.influxdb import InfluxDBClient, write_sensor_data, query_sensor_data
from src.database.postgresql import (
    get_async_session, 
    init_database, 
    close_database, 
    check_database_health,
    SensorDevice,
    SubstrateType,
    SubstrateBatch,
    SubstrateBatchComponent,
    AlertRule
)

__all__ = [
    # InfluxDB
    'InfluxDBClient', 
    'write_sensor_data', 
    'query_sensor_data',
    # PostgreSQL
    'get_async_session',
    'init_database',
    'close_database', 
    'check_database_health',
    'SensorDevice',
    'SubstrateType',
    'SubstrateBatch',
    'SubstrateBatchComponent',
    'AlertRule'
]