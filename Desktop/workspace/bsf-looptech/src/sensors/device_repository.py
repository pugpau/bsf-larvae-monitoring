"""
Repository for sensor device management using PostgreSQL.
This repository handles sensor device registration, configuration, and status management.
Sensor readings remain in InfluxDB for time-series data.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload

from src.database.postgresql import (
    SensorDevice as SensorDeviceDB,
    AlertRule as AlertRuleDB,
    get_async_session
)
from src.sensors.models import (
    SensorDevice, SensorAlert, SensorThreshold,
    SensorDeviceCreate, SensorDeviceUpdate, SensorThresholdCreate,
    SensorDeviceResponse, SensorThresholdResponse
)

logger = logging.getLogger(__name__)


class SensorDeviceRepository:
    """Repository for sensor device management using PostgreSQL."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Sensor Device Operations
    
    async def create_sensor_device(self, device_data: SensorDeviceCreate) -> Optional[SensorDeviceResponse]:
        """Create a new sensor device."""
        try:
            # Create database model
            db_device = SensorDeviceDB(
                device_id=device_data.device_id,
                device_type=device_data.device_type,
                name=device_data.name,
                description=device_data.description,
                farm_id=device_data.farm_id,
                location=device_data.location,
                position_x=device_data.x_position,
                position_y=device_data.y_position,
                position_z=device_data.z_position,
                status=getattr(device_data, 'status', 'active'),
                substrate_batch_id=device_data.substrate_batch_id
            )
            
            # Add to session
            self.session.add(db_device)
            await self.session.commit()
            await self.session.refresh(db_device)
            
            logger.info(f"Created sensor device: {db_device.device_id}")
            
            # Convert to response model
            return await self._to_sensor_device_response(db_device)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating sensor device: {e}")
            return None
    
    async def get_sensor_device(self, device_id: str) -> Optional[SensorDeviceResponse]:
        """Get a sensor device by device_id."""
        try:
            # Query database
            result = await self.session.execute(
                select(SensorDeviceDB)
                .options(selectinload(SensorDeviceDB.substrate_batch))
                .where(SensorDeviceDB.device_id == device_id)
            )
            db_device = result.scalar_one_or_none()
            
            if not db_device:
                return None
            
            return await self._to_sensor_device_response(db_device)
            
        except Exception as e:
            logger.error(f"Error getting sensor device {device_id}: {e}")
            return None
    
    async def get_sensor_device_by_uuid(self, device_uuid: str) -> Optional[SensorDeviceResponse]:
        """Get a sensor device by UUID."""
        try:
            # Query database
            result = await self.session.execute(
                select(SensorDeviceDB)
                .options(selectinload(SensorDeviceDB.substrate_batch))
                .where(SensorDeviceDB.id == device_uuid)
            )
            db_device = result.scalar_one_or_none()
            
            if not db_device:
                return None
            
            return await self._to_sensor_device_response(db_device)
            
        except Exception as e:
            logger.error(f"Error getting sensor device by UUID {device_uuid}: {e}")
            return None
    
    async def get_sensor_devices(
        self,
        farm_id: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None
    ) -> List[SensorDeviceResponse]:
        """Get sensor devices with optional filters."""
        try:
            # Build query
            query = select(SensorDeviceDB).options(
                selectinload(SensorDeviceDB.substrate_batch)
            )

            if farm_id:
                query = query.where(SensorDeviceDB.farm_id == farm_id)
            if device_type:
                query = query.where(SensorDeviceDB.device_type == device_type)
            if status:
                query = query.where(SensorDeviceDB.status == status)
            if location:
                query = query.where(SensorDeviceDB.location == location)
            if substrate_batch_id:
                query = query.where(SensorDeviceDB.substrate_batch_id == substrate_batch_id)

            query = query.order_by(SensorDeviceDB.created_at.desc())

            # Execute query
            result = await self.session.execute(query)
            db_devices = result.scalars().all()

            # Convert to response models
            devices = []
            for db_device in db_devices:
                response = await self._to_sensor_device_response(db_device)
                if response:
                    devices.append(response)

            return devices

        except Exception as e:
            logger.error(f"Error getting sensor devices: {e}")
            return []

    async def get_device_status_summary(
        self,
        farm_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get summary of device statuses (online, offline, error counts)."""
        try:
            from sqlalchemy import func
            from datetime import timedelta

            # Build base query - exclude inactive devices
            query = select(SensorDeviceDB).where(
                SensorDeviceDB.status != 'inactive'
            )

            if farm_id:
                query = query.where(SensorDeviceDB.farm_id == farm_id)

            # Execute query
            result = await self.session.execute(query)
            db_devices = result.scalars().all()

            # Count devices by status
            # A device is considered "online" if last_seen is within 5 minutes
            # A device is "offline" if last_seen is older than 5 minutes or null
            # A device is "error" if status is 'error'
            online_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

            online_count = 0
            offline_count = 0
            error_count = 0

            for device in db_devices:
                device_status = getattr(device, 'status', 'active')
                last_seen = getattr(device, 'last_seen', None)
                is_online = getattr(device, 'is_online', False)

                if device_status == 'error':
                    error_count += 1
                elif is_online and last_seen and last_seen.replace(tzinfo=timezone.utc) > online_threshold:
                    online_count += 1
                else:
                    offline_count += 1

            total = len(db_devices)

            return {
                'online': online_count,
                'offline': offline_count,
                'error': error_count,
                'total': total
            }

        except Exception as e:
            logger.error(f"Error getting device status summary: {e}")
            return {'online': 0, 'offline': 0, 'error': 0, 'total': 0}
    
    async def update_sensor_device(self, device_id: str, device_data: SensorDeviceCreate) -> Optional[SensorDeviceResponse]:
        """Update a sensor device."""
        try:
            # Get existing device
            result = await self.session.execute(
                select(SensorDeviceDB).where(SensorDeviceDB.device_id == device_id)
            )
            db_device = result.scalar_one_or_none()
            
            if not db_device:
                return None
            
            # Update fields
            setattr(db_device, 'device_type', device_data.device_type)
            setattr(db_device, 'name', device_data.name)
            setattr(db_device, 'description', device_data.description)
            setattr(db_device, 'farm_id', device_data.farm_id)
            setattr(db_device, 'location', device_data.location)
            setattr(db_device, 'position_x', device_data.x_position)
            setattr(db_device, 'position_y', device_data.y_position)
            setattr(db_device, 'position_z', device_data.z_position)
            setattr(db_device, 'status', getattr(device_data, 'status', 'active'))
            setattr(db_device, 'substrate_batch_id', device_data.substrate_batch_id)
            setattr(db_device, 'updated_at', datetime.utcnow())
            
            await self.session.commit()
            await self.session.refresh(db_device)
            
            logger.info(f"Updated sensor device: {device_id}")
            
            return await self._to_sensor_device_response(db_device)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating sensor device {device_id}: {e}")
            return None
    
    async def partial_update_sensor_device(self, device_id: str, update_data: SensorDeviceUpdate) -> Optional[SensorDeviceResponse]:
        """Partially update a sensor device with only provided fields."""
        try:
            # Get existing device
            result = await self.session.execute(
                select(SensorDeviceDB).where(SensorDeviceDB.device_id == device_id)
            )
            db_device = result.scalar_one_or_none()

            if not db_device:
                return None

            # Update only provided fields
            if update_data.name is not None:
                setattr(db_device, 'name', update_data.name)
            if update_data.description is not None:
                setattr(db_device, 'description', update_data.description)
            if update_data.location is not None:
                setattr(db_device, 'location', update_data.location)
            if update_data.x_position is not None:
                setattr(db_device, 'position_x', update_data.x_position)
            if update_data.y_position is not None:
                setattr(db_device, 'position_y', update_data.y_position)
            if update_data.z_position is not None:
                setattr(db_device, 'position_z', update_data.z_position)
            if update_data.status is not None:
                setattr(db_device, 'status', update_data.status)
            # Note: metadata column doesn't exist in SensorDevice model
            # Metadata support would require adding a JSON column to the model

            setattr(db_device, 'updated_at', datetime.utcnow())

            await self.session.commit()
            await self.session.refresh(db_device)

            logger.info(f"Partially updated sensor device: {device_id}")

            return await self._to_sensor_device_response(db_device)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error partially updating sensor device {device_id}: {e}")
            return None

    async def update_device_last_seen(self, device_id: str, timestamp: datetime) -> bool:
        """Update the last_seen timestamp and set device as online."""
        try:
            # Update device
            await self.session.execute(
                update(SensorDeviceDB)
                .where(SensorDeviceDB.device_id == device_id)
                .values(
                    last_seen=timestamp,
                    is_online=True,
                    updated_at=datetime.utcnow()
                )
            )
            await self.session.commit()
            
            logger.debug(f"Updated last_seen for device {device_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating device last_seen {device_id}: {e}")
            return False
    
    async def delete_sensor_device(self, device_id: str) -> bool:
        """Delete a sensor device."""
        try:
            # Delete the device
            await self.session.execute(
                delete(SensorDeviceDB).where(SensorDeviceDB.device_id == device_id)
            )
            await self.session.commit()
            
            logger.info(f"Deleted sensor device: {device_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting sensor device {device_id}: {e}")
            return False
    
    # Alert Rule Operations
    
    async def create_alert_rule(self, rule_data: SensorThresholdCreate) -> Optional[SensorThresholdResponse]:
        """Create a new alert rule (threshold)."""
        try:
            # Determine operator based on thresholds
            if rule_data.high_threshold is not None and rule_data.low_threshold is not None:
                operator = "range"
            elif rule_data.high_threshold is not None:
                operator = "<="
            elif rule_data.low_threshold is not None:
                operator = ">="
            else:
                logger.warning("No thresholds specified for alert rule")
                return None
            
            # Create database model
            db_rule = AlertRuleDB(
                name=f"{rule_data.measurement_type} threshold for {rule_data.device_type}",
                description=f"Threshold monitoring for {rule_data.measurement_type}",
                farm_id=rule_data.farm_id,
                device_id=None,  # Not in SensorThresholdCreate model
                measurement_type=rule_data.measurement_type,
                min_threshold=rule_data.low_threshold,
                max_threshold=rule_data.high_threshold,
                operator=operator,
                severity="warning"
            )
            
            # Add to session
            self.session.add(db_rule)
            await self.session.commit()
            await self.session.refresh(db_rule)
            
            logger.info(f"Created alert rule: {db_rule.id}")
            
            # Convert to response model
            return await self._to_threshold_response(db_rule)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating alert rule: {e}")
            return None
    
    async def get_alert_rules(
        self,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        measurement_type: Optional[str] = None
    ) -> List[SensorThresholdResponse]:
        """Get alert rules with optional filters."""
        try:
            # Build query
            query = select(AlertRuleDB).where(AlertRuleDB.is_active == True)
            
            if farm_id:
                query = query.where(AlertRuleDB.farm_id == farm_id)
            if device_id:
                query = query.where(AlertRuleDB.device_id == device_id)
            if measurement_type:
                query = query.where(AlertRuleDB.measurement_type == measurement_type)
            
            query = query.order_by(AlertRuleDB.created_at.desc())
            
            # Execute query
            result = await self.session.execute(query)
            db_rules = result.scalars().all()
            
            # Convert to response models
            rules = []
            for db_rule in db_rules:
                response = await self._to_threshold_response(db_rule)
                if response:
                    rules.append(response)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            return []
    
    async def update_alert_rule(self, rule_id: str, rule_data: SensorThresholdCreate) -> Optional[SensorThresholdResponse]:
        """Update an alert rule."""
        try:
            # Get existing rule
            result = await self.session.execute(
                select(AlertRuleDB).where(AlertRuleDB.id == rule_id)
            )
            db_rule = result.scalar_one_or_none()
            
            if not db_rule:
                return None
            
            # Update fields
            setattr(db_rule, 'farm_id', rule_data.farm_id)
            # Note: device_id not in SensorThresholdCreate model, keeping existing value
            setattr(db_rule, 'measurement_type', rule_data.measurement_type)
            setattr(db_rule, 'min_threshold', rule_data.low_threshold)
            setattr(db_rule, 'max_threshold', rule_data.high_threshold)
            setattr(db_rule, 'updated_at', datetime.utcnow())
            
            await self.session.commit()
            await self.session.refresh(db_rule)
            
            logger.info(f"Updated alert rule: {rule_id}")
            
            return await self._to_threshold_response(db_rule)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating alert rule {rule_id}: {e}")
            return None
    
    async def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        try:
            # Delete the rule
            await self.session.execute(
                delete(AlertRuleDB).where(AlertRuleDB.id == rule_id)
            )
            await self.session.commit()
            
            logger.info(f"Deleted alert rule: {rule_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting alert rule {rule_id}: {e}")
            return False
    
    # Helper methods
    
    async def _to_sensor_device_response(self, db_device: SensorDeviceDB) -> Optional[SensorDeviceResponse]:
        """Convert database model to response model."""
        try:
            from datetime import timedelta

            # Calculate display status based on last_seen and is_online
            db_status = getattr(db_device, 'status', 'active')
            last_seen = getattr(db_device, 'last_seen', None)
            is_online = getattr(db_device, 'is_online', False)

            # Determine display status
            if db_status == 'inactive':
                display_status = 'inactive'
            elif db_status == 'error':
                display_status = 'error'
            else:
                # For active devices, check if they're online based on last_seen
                online_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
                if is_online and last_seen and last_seen.replace(tzinfo=timezone.utc) > online_threshold:
                    display_status = 'online'
                else:
                    display_status = 'offline'

            return SensorDeviceResponse(
                id=str(getattr(db_device, 'id')),
                device_id=getattr(db_device, 'device_id'),
                device_type=getattr(db_device, 'device_type'),
                name=getattr(db_device, 'name'),
                description=getattr(db_device, 'description'),
                farm_id=getattr(db_device, 'farm_id'),
                location=getattr(db_device, 'location'),
                x_position=getattr(db_device, 'position_x'),
                y_position=getattr(db_device, 'position_y'),
                z_position=getattr(db_device, 'position_z'),
                status=display_status,  # Use computed display status
                last_seen=getattr(db_device, 'last_seen'),
                substrate_batch_id=str(getattr(db_device, 'substrate_batch_id')) if getattr(db_device, 'substrate_batch_id') else None,
                created_at=getattr(db_device, 'created_at'),
                updated_at=getattr(db_device, 'updated_at'),
                metadata=None  # Can be extended later if needed
            )
        except Exception as e:
            logger.error(f"Error converting sensor device to response: {e}")
            return None
    
    async def _to_threshold_response(self, db_rule: AlertRuleDB) -> Optional[SensorThresholdResponse]:
        """Convert database model to threshold response model."""
        try:
            return SensorThresholdResponse(
                id=str(getattr(db_rule, 'id')),
                farm_id=getattr(db_rule, 'farm_id'),
                device_type="",  # Not stored in alert rules, could be derived
                measurement_type=getattr(db_rule, 'measurement_type'),
                high_threshold=getattr(db_rule, 'max_threshold'),
                low_threshold=getattr(db_rule, 'min_threshold'),
                unit="",  # Not stored in alert rules, could be extended
                location=None,  # Not stored in alert rules
                substrate_batch_id=None,  # Not stored in alert rules
                created_at=getattr(db_rule, 'created_at'),
                updated_at=getattr(db_rule, 'updated_at')
            )
        except Exception as e:
            logger.error(f"Error converting alert rule to threshold response: {e}")
            return None


# Dependency injection helper
async def get_sensor_device_repository():
    """Get sensor device repository with database session."""
    async for session in get_async_session():
        yield SensorDeviceRepository(session)