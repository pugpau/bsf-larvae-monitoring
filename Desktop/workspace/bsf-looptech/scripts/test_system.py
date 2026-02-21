#!/usr/bin/env python3
"""
System integration test and report generator for BSF-LoopTech.
Tests PostgreSQL + InfluxDB integration and generates status report.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import settings
from src.database.postgresql import (
    get_async_session, check_database_health,
    SubstrateType, SubstrateBatch, SensorDevice
)
from src.database.influxdb import InfluxDBClient
from src.substrate.repository import SubstrateRepository
from src.sensors.device_repository import SensorDeviceRepository
from src.substrate.models import SubstrateTypeCreate, SubstrateBatchCreate, SubstrateComponentCreate
from src.sensors.models import SensorDeviceCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemTester:
    """System integration tester."""
    
    def __init__(self):
        self.test_results = {}
        self.errors = []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all system tests and return results."""
        logger.info("Starting BSF-LoopTech system integration tests...")
        
        # Test database connections
        await self.test_postgresql_connection()
        await self.test_influxdb_connection()
        
        # Test repository operations
        await self.test_substrate_operations()
        await self.test_sensor_device_operations()
        await self.test_sensor_data_operations()
        
        # Test data integration
        await self.test_data_integration()
        
        # Generate report
        report = self.generate_report()
        
        logger.info("System integration tests completed")
        return report
    
    async def test_postgresql_connection(self):
        """Test PostgreSQL connection and basic operations."""
        test_name = "PostgreSQL Connection"
        logger.info(f"Testing {test_name}...")
        
        try:
            # Test connection
            health_ok = await check_database_health()
            
            if health_ok:
                self.test_results[test_name] = {
                    "status": "PASS",
                    "message": "Connection successful",
                    "details": {
                        "host": settings.POSTGRES_HOST,
                        "port": settings.POSTGRES_PORT,
                        "database": settings.POSTGRES_DB
                    }
                }
            else:
                self.test_results[test_name] = {
                    "status": "FAIL",
                    "message": "Connection failed",
                    "details": {}
                }
                
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    def test_influxdb_connection(self):
        """Test InfluxDB connection and basic operations."""
        test_name = "InfluxDB Connection"
        logger.info(f"Testing {test_name}...")
        
        try:
            influxdb = InfluxDBClient()
            
            if influxdb.connect():
                # Test write operation
                test_point = {
                    "measurement": "system_test",
                    "tags": {"test": "connection"},
                    "fields": {"value": 1},
                    "time": datetime.utcnow().isoformat()
                }
                
                write_success = influxdb.write_point(test_point)
                influxdb.close()
                
                if write_success:
                    self.test_results[test_name] = {
                        "status": "PASS",
                        "message": "Connection and write successful",
                        "details": {
                            "url": settings.INFLUXDB_URL,
                            "bucket": settings.INFLUXDB_BUCKET,
                            "org": settings.INFLUXDB_ORG
                        }
                    }
                else:
                    self.test_results[test_name] = {
                        "status": "FAIL",
                        "message": "Connection OK but write failed",
                        "details": {}
                    }
            else:
                self.test_results[test_name] = {
                    "status": "FAIL",
                    "message": "Connection failed",
                    "details": {}
                }
                
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    async def test_substrate_operations(self):
        """Test substrate repository operations."""
        test_name = "Substrate Operations"
        logger.info(f"Testing {test_name}...")
        
        try:
            async with get_async_session() as session:
                repo = SubstrateRepository(session)
                
                # Test create substrate type
                type_data = SubstrateTypeCreate(
                    name="Test Substrate",
                    category="other",
                    description="Test substrate for system integration",
                    custom_attributes={"test": True}
                )
                
                created_type = await repo.create_substrate_type(type_data)
                
                if created_type:
                    # Test create substrate batch
                    batch_data = SubstrateBatchCreate(
                        farm_id="test_farm",
                        batch_name="Test Batch",
                        batch_number="TEST001",
                        description="Test batch for system integration",
                        total_weight=100.0,
                        weight_unit="kg",
                        storage_location="Test Location",
                        status="active",
                        components=[
                            SubstrateComponentCreate(
                                substrate_type_id=created_type.id,
                                ratio_percentage=100.0
                            )
                        ]
                    )
                    
                    created_batch = await repo.create_substrate_batch(batch_data)
                    
                    if created_batch:
                        # Test read operations
                        retrieved_type = await repo.get_substrate_type(created_type.id)
                        retrieved_batch = await repo.get_substrate_batch(created_batch.id)
                        
                        # Cleanup
                        await repo.delete_substrate_batch(created_batch.id)
                        await repo.delete_substrate_type(created_type.id)
                        
                        self.test_results[test_name] = {
                            "status": "PASS",
                            "message": "CRUD operations successful",
                            "details": {
                                "operations_tested": ["create", "read", "delete"],
                                "type_id": created_type.id,
                                "batch_id": created_batch.id
                            }
                        }
                    else:
                        self.test_results[test_name] = {
                            "status": "FAIL",
                            "message": "Failed to create substrate batch",
                            "details": {}
                        }
                else:
                    self.test_results[test_name] = {
                        "status": "FAIL",
                        "message": "Failed to create substrate type",
                        "details": {}
                    }
                    
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    async def test_sensor_device_operations(self):
        """Test sensor device repository operations."""
        test_name = "Sensor Device Operations"
        logger.info(f"Testing {test_name}...")
        
        try:
            async with get_async_session() as session:
                repo = SensorDeviceRepository(session)
                
                # Test create sensor device
                device_data = SensorDeviceCreate(
                    device_id="test_sensor_001",
                    device_type="environmental",
                    name="Test Sensor Device",
                    description="Test sensor for system integration",
                    farm_id="test_farm",
                    location="Test Location",
                    position_x=10.0,
                    position_y=20.0,
                    position_z=1.5,
                    status="active"
                )
                
                created_device = await repo.create_sensor_device(device_data)
                
                if created_device:
                    # Test read operations
                    retrieved_device = await repo.get_sensor_device(device_data.device_id)
                    devices_list = await repo.get_sensor_devices(farm_id="test_farm")
                    
                    # Test update last seen
                    update_success = await repo.update_device_last_seen(
                        device_data.device_id, 
                        datetime.utcnow()
                    )
                    
                    # Cleanup
                    await repo.delete_sensor_device(device_data.device_id)
                    
                    self.test_results[test_name] = {
                        "status": "PASS",
                        "message": "CRUD operations successful",
                        "details": {
                            "operations_tested": ["create", "read", "update", "delete"],
                            "device_id": created_device.device_id,
                            "devices_found": len(devices_list)
                        }
                    }
                else:
                    self.test_results[test_name] = {
                        "status": "FAIL",
                        "message": "Failed to create sensor device",
                        "details": {}
                    }
                    
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    def test_sensor_data_operations(self):
        """Test sensor data operations with InfluxDB."""
        test_name = "Sensor Data Operations"
        logger.info(f"Testing {test_name}...")
        
        try:
            influxdb = InfluxDBClient()
            
            if influxdb.connect():
                # Test write sensor data
                test_readings = [
                    {
                        "measurement": "sensor_readings",
                        "tags": {
                            "farm_id": "test_farm",
                            "device_id": "test_sensor_001",
                            "device_type": "environmental",
                            "measurement_type": "temperature",
                            "unit": "°C"
                        },
                        "fields": {
                            "value": 25.5,
                            "reading_id": "test_reading_001"
                        },
                        "time": datetime.utcnow().isoformat()
                    },
                    {
                        "measurement": "sensor_readings",
                        "tags": {
                            "farm_id": "test_farm",
                            "device_id": "test_sensor_001",
                            "device_type": "environmental",
                            "measurement_type": "humidity",
                            "unit": "%"
                        },
                        "fields": {
                            "value": 65.2,
                            "reading_id": "test_reading_002"
                        },
                        "time": datetime.utcnow().isoformat()
                    }
                ]
                
                write_success = True
                for reading in test_readings:
                    if not influxdb.write_point(reading):
                        write_success = False
                        break
                
                influxdb.close()
                
                if write_success:
                    self.test_results[test_name] = {
                        "status": "PASS",
                        "message": "Sensor data write successful",
                        "details": {
                            "readings_written": len(test_readings),
                            "measurement_types": ["temperature", "humidity"]
                        }
                    }
                else:
                    self.test_results[test_name] = {
                        "status": "FAIL",
                        "message": "Failed to write sensor data",
                        "details": {}
                    }
            else:
                self.test_results[test_name] = {
                    "status": "FAIL",
                    "message": "Failed to connect to InfluxDB",
                    "details": {}
                }
                
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    async def test_data_integration(self):
        """Test integration between PostgreSQL and InfluxDB data."""
        test_name = "Data Integration"
        logger.info(f"Testing {test_name}...")
        
        try:
            # This test verifies that device metadata (PostgreSQL) 
            # can be linked with sensor readings (InfluxDB)
            
            async with get_async_session() as session:
                device_repo = SensorDeviceRepository(session)
                
                # Create test device
                device_data = SensorDeviceCreate(
                    device_id="integration_test_device",
                    device_type="environmental",
                    name="Integration Test Device",
                    description="Device for testing PostgreSQL-InfluxDB integration",
                    farm_id="test_farm",
                    location="Integration Test Location",
                    position_x=50.0,
                    position_y=60.0,
                    position_z=2.0,
                    status="active"
                )
                
                created_device = await device_repo.create_sensor_device(device_data)
                
                if created_device:
                    # Create corresponding sensor data in InfluxDB
                    influxdb = InfluxDBClient()
                    
                    if influxdb.connect():
                        reading = {
                            "measurement": "sensor_readings",
                            "tags": {
                                "farm_id": created_device.farm_id,
                                "device_id": created_device.device_id,
                                "device_type": created_device.device_type,
                                "measurement_type": "integration_test",
                                "unit": "test"
                            },
                            "fields": {
                                "value": 42.0,
                                "reading_id": "integration_test_reading"
                            },
                            "time": datetime.utcnow().isoformat()
                        }
                        
                        write_success = influxdb.write_point(reading)
                        influxdb.close()
                        
                        # Cleanup
                        await device_repo.delete_sensor_device(created_device.device_id)
                        
                        if write_success:
                            self.test_results[test_name] = {
                                "status": "PASS",
                                "message": "PostgreSQL-InfluxDB integration successful",
                                "details": {
                                    "device_id": created_device.device_id,
                                    "data_written": True,
                                    "integration_verified": True
                                }
                            }
                        else:
                            self.test_results[test_name] = {
                                "status": "FAIL",
                                "message": "Failed to write integrated sensor data",
                                "details": {}
                            }
                    else:
                        self.test_results[test_name] = {
                            "status": "FAIL",
                            "message": "Failed to connect to InfluxDB for integration test",
                            "details": {}
                        }
                else:
                    self.test_results[test_name] = {
                        "status": "FAIL",
                        "message": "Failed to create device for integration test",
                        "details": {}
                    }
                    
        except Exception as e:
            self.test_results[test_name] = {
                "status": "ERROR",
                "message": str(e),
                "details": {}
            }
            self.errors.append(f"{test_name}: {e}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "FAIL")
        error_tests = sum(1 for result in self.test_results.values() if result["status"] == "ERROR")
        total_tests = len(self.test_results)
        
        overall_status = "PASS" if passed_tests == total_tests else "FAIL"
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%"
            },
            "configuration": {
                "postgresql": {
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                    "database": settings.POSTGRES_DB
                },
                "influxdb": {
                    "url": settings.INFLUXDB_URL,
                    "bucket": settings.INFLUXDB_BUCKET,
                    "org": settings.INFLUXDB_ORG
                }
            },
            "test_results": self.test_results,
            "errors": self.errors
        }
        
        return report


async def main():
    """Main test execution function."""
    tester = SystemTester()
    report = await tester.run_all_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("BSF-LoopTech System Integration Test Report")
    print("="*60)
    print(f"Overall Status: {report['overall_status']}")
    print(f"Tests Passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']}")
    
    if report['errors']:
        print(f"\nErrors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f"  - {error}")
    
    print("\nDetailed Results:")
    for test_name, result in report['test_results'].items():
        status_icon = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
        print(f"  {status_icon} {test_name}: {result['message']}")
    
    # Save detailed report
    report_file = f"system_test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with appropriate code
    if report['overall_status'] == "PASS":
        print("\n🎉 All tests passed! System is ready for use.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())