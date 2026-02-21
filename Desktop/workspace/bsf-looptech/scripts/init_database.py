#!/usr/bin/env python3
"""
Database initialization script for BSF-LoopTech system.
This script initializes both PostgreSQL and InfluxDB databases.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import settings
from src.database.postgresql import init_database, check_database_health
from src.database.influxdb import InfluxDBClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_postgresql():
    """Initialize PostgreSQL database."""
    try:
        logger.info("Initializing PostgreSQL database...")
        
        # Check database health
        health_ok = await check_database_health()
        if not health_ok:
            logger.error("PostgreSQL database health check failed")
            logger.info("Please ensure PostgreSQL is running and accessible with the following settings:")
            logger.info(f"  Host: {settings.POSTGRES_HOST}")
            logger.info(f"  Port: {settings.POSTGRES_PORT}")
            logger.info(f"  Database: {settings.POSTGRES_DB}")
            logger.info(f"  User: {settings.POSTGRES_USER}")
            return False
        
        # Initialize database tables
        await init_database()
        logger.info("PostgreSQL database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        return False


def init_influxdb():
    """Initialize InfluxDB database."""
    try:
        logger.info("Initializing InfluxDB database...")
        
        # Create InfluxDB client
        influxdb = InfluxDBClient()
        
        # Test connection
        if not influxdb.connect():
            logger.error("InfluxDB connection failed")
            logger.info("Please ensure InfluxDB is running and accessible with the following settings:")
            logger.info(f"  URL: {settings.INFLUXDB_URL}")
            logger.info(f"  Organization: {settings.INFLUXDB_ORG}")
            logger.info(f"  Bucket: {settings.INFLUXDB_BUCKET}")
            return False
        
        # Check if bucket exists, create if not
        try:
            # Try to write a test point
            test_point = {
                "measurement": "system_test",
                "tags": {"source": "init_script"},
                "fields": {"value": 1},
                "time": "2023-01-01T00:00:00Z"
            }
            
            success = influxdb.write_point(test_point)
            if success:
                logger.info("InfluxDB bucket is accessible and writable")
                
                # Clean up test point (optional)
                # Note: In production, you might want to keep this for monitoring
                
            else:
                logger.warning("InfluxDB write test failed, but connection is OK")
                
        except Exception as e:
            logger.warning(f"InfluxDB test write failed: {e}")
            logger.info("This might be normal if the bucket doesn't exist yet")
        
        finally:
            influxdb.close()
        
        logger.info("InfluxDB database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB: {e}")
        return False


async def create_sample_data():
    """Create sample data for testing."""
    try:
        logger.info("Creating sample data...")
        
        from src.database.postgresql import get_async_session
        from src.substrate.repository import SubstrateRepository
        from src.sensors.device_repository import SensorDeviceRepository
        from src.substrate.models import SubstrateTypeCreate, SubstrateBatchCreate, SubstrateComponentCreate
        from src.sensors.models import SensorDeviceCreate
        
        async with get_async_session() as session:
            substrate_repo = SubstrateRepository(session)
            device_repo = SensorDeviceRepository(session)
            
            # Create sample substrate types
            substrate_types = [
                SubstrateTypeCreate(
                    name="下水汚泥",
                    category="sewage_sludge",
                    description="下水処理場からの汚泥",
                    custom_attributes={"moisture_content": "80%", "organic_matter": "60%"}
                ),
                SubstrateTypeCreate(
                    name="豚糞",
                    category="pig_manure",
                    description="豚の糞尿",
                    custom_attributes={"nitrogen_content": "3%", "phosphorus_content": "2%"}
                ),
                SubstrateTypeCreate(
                    name="おが屑",
                    category="sawdust",
                    description="木材加工時のおが屑",
                    custom_attributes={"carbon_nitrogen_ratio": "30:1", "moisture_content": "10%"}
                )
            ]
            
            created_types = []
            for type_data in substrate_types:
                created_type = await substrate_repo.create_substrate_type(type_data)
                if created_type:
                    created_types.append(created_type)
                    logger.info(f"Created substrate type: {created_type.name}")
            
            # Create sample substrate batch
            if len(created_types) >= 2:
                batch_data = SubstrateBatchCreate(
                    farm_id="farm_001",
                    batch_name="テストバッチ001",
                    batch_number="B001",
                    description="初期テスト用バッチ",
                    total_weight=100.0,
                    weight_unit="kg",
                    storage_location="区画A-1",
                    status="active",
                    components=[
                        SubstrateComponentCreate(
                            substrate_type_id=created_types[0].id,
                            ratio_percentage=70.0
                        ),
                        SubstrateComponentCreate(
                            substrate_type_id=created_types[1].id,
                            ratio_percentage=30.0
                        )
                    ]
                )
                
                created_batch = await substrate_repo.create_substrate_batch(batch_data)
                if created_batch:
                    logger.info(f"Created substrate batch: {created_batch.batch_name}")
                    
                    # Create sample sensor device
                    device_data = SensorDeviceCreate(
                        device_id="sensor_001",
                        device_type="environmental",
                        name="環境センサー001",
                        description="温度・湿度・ガス濃度測定",
                        farm_id="farm_001",
                        location="区画A-1",
                        position_x=10.5,
                        position_y=20.3,
                        position_z=1.5,
                        status="active",
                        substrate_batch_id=created_batch.id
                    )
                    
                    created_device = await device_repo.create_sensor_device(device_data)
                    if created_device:
                        logger.info(f"Created sensor device: {created_device.device_id}")
        
        logger.info("Sample data created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        return False


async def main():
    """Main initialization function."""
    logger.info("Starting BSF-LoopTech database initialization...")
    
    # Show configuration
    logger.info("Configuration:")
    logger.info(f"  PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    logger.info(f"  InfluxDB: {settings.INFLUXDB_URL}/{settings.INFLUXDB_BUCKET}")
    
    # Initialize databases
    postgresql_ok = await init_postgresql()
    influxdb_ok = init_influxdb()
    
    if not postgresql_ok or not influxdb_ok:
        logger.error("Database initialization failed")
        return False
    
    # Create sample data
    sample_data_ok = await create_sample_data()
    
    if sample_data_ok:
        logger.info("Database initialization completed successfully with sample data")
    else:
        logger.warning("Database initialization completed, but sample data creation failed")
    
    logger.info("Database initialization script finished")
    return True


if __name__ == "__main__":
    # Run the initialization
    success = asyncio.run(main())
    
    if success:
        print("\n✅ Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Start the FastAPI server: uvicorn src.main:app --reload")
        print("2. Visit the API documentation: http://localhost:8000/docs")
        print("3. Start the React frontend: cd frontend && npm start")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check the logs above and fix any issues.")
        sys.exit(1)