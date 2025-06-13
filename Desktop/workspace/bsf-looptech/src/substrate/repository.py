"""
Repository for substrate data storage and retrieval using PostgreSQL.
This repository handles substrate types, batches, and related operations.
"""

import logging
import json
from typing import List, Optional, AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from src.database.postgresql import (
    SubstrateType as SubstrateTypeDB,
    SubstrateBatch as SubstrateBatchDB,
    SubstrateBatchComponent as SubstrateBatchComponentDB,
    get_async_session
)
from src.substrate.models import (
    SubstrateComponent,
    SubstrateTypeCreate, SubstrateBatchCreate,
    SubstrateTypeResponse, SubstrateBatchResponse
)

logger = logging.getLogger(__name__)


class SubstrateRepository:
    """Repository for substrate data management using PostgreSQL."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Substrate Type Operations
    
    async def create_substrate_type(self, substrate_type_data: SubstrateTypeCreate) -> Optional[SubstrateTypeResponse]:
        """Create a new substrate type."""
        try:
            # Serialize custom attributes to JSON
            custom_attributes_json = None
            if substrate_type_data.custom_attributes:
                custom_attributes_json = json.dumps(substrate_type_data.custom_attributes)
            
            # Create database model
            db_substrate_type = SubstrateTypeDB(
                name=substrate_type_data.name,
                category=substrate_type_data.category,
                description=substrate_type_data.description,
                custom_attributes=custom_attributes_json
            )
            
            # Add to session
            self.session.add(db_substrate_type)
            await self.session.commit()
            await self.session.refresh(db_substrate_type)
            
            logger.info(f"Created substrate type: {db_substrate_type.id}")
            
            # Convert to response model
            return await self._to_substrate_type_response(db_substrate_type)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating substrate type: {e}")
            return None
    
    async def get_substrate_type(self, substrate_type_id: str) -> Optional[SubstrateTypeResponse]:
        """Get a substrate type by ID."""
        try:
            # Query database
            result = await self.session.execute(
                select(SubstrateTypeDB).where(SubstrateTypeDB.id == substrate_type_id)
            )
            db_substrate_type = result.scalar_one_or_none()
            
            if not db_substrate_type:
                return None
            
            return await self._to_substrate_type_response(db_substrate_type)
            
        except Exception as e:
            logger.error(f"Error getting substrate type {substrate_type_id}: {e}")
            return None
    
    async def get_all_substrate_types(self) -> List[SubstrateTypeResponse]:
        """Get all substrate types."""
        try:
            # Query database
            result = await self.session.execute(
                select(SubstrateTypeDB).order_by(SubstrateTypeDB.created_at.desc())
            )
            db_substrate_types = result.scalars().all()
            
            # Convert to response models
            substrate_types = []
            for db_type in db_substrate_types:
                response = await self._to_substrate_type_response(db_type)
                if response:
                    substrate_types.append(response)
            
            return substrate_types
            
        except Exception as e:
            logger.error(f"Error getting all substrate types: {e}")
            return []
    
    async def update_substrate_type(self, substrate_type_id: str, substrate_type_data: SubstrateTypeCreate) -> Optional[SubstrateTypeResponse]:
        """Update a substrate type."""
        try:
            # Get existing record
            result = await self.session.execute(
                select(SubstrateTypeDB).where(SubstrateTypeDB.id == substrate_type_id)
            )
            db_substrate_type = result.scalar_one_or_none()
            
            if not db_substrate_type:
                return None
            
            # Serialize custom attributes to JSON
            custom_attributes_json = None
            if substrate_type_data.custom_attributes:
                custom_attributes_json = json.dumps(substrate_type_data.custom_attributes)
            
            # Update fields
            setattr(db_substrate_type, 'name', substrate_type_data.name)
            setattr(db_substrate_type, 'category', substrate_type_data.category)
            setattr(db_substrate_type, 'description', substrate_type_data.description)
            setattr(db_substrate_type, 'custom_attributes', custom_attributes_json)
            setattr(db_substrate_type, 'updated_at', datetime.now(timezone.utc))
            
            await self.session.commit()
            await self.session.refresh(db_substrate_type)
            
            logger.info(f"Updated substrate type: {substrate_type_id}")
            
            return await self._to_substrate_type_response(db_substrate_type)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating substrate type {substrate_type_id}: {e}")
            return None
    
    async def delete_substrate_type(self, substrate_type_id: str) -> bool:
        """Delete a substrate type."""
        try:
            # Check if type is used in any batches
            result = await self.session.execute(
                select(SubstrateBatchComponentDB).where(
                    SubstrateBatchComponentDB.substrate_type_id == substrate_type_id
                )
            )
            components = result.scalars().all()
            
            if components:
                logger.warning(f"Cannot delete substrate type {substrate_type_id}: used in {len(components)} batch components")
                return False
            
            # Delete the substrate type
            await self.session.execute(
                delete(SubstrateTypeDB).where(SubstrateTypeDB.id == substrate_type_id)
            )
            await self.session.commit()
            
            logger.info(f"Deleted substrate type: {substrate_type_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting substrate type {substrate_type_id}: {e}")
            return False
    
    # Substrate Batch Operations
    
    async def create_substrate_batch(self, batch_data: SubstrateBatchCreate) -> Optional[SubstrateBatchResponse]:
        """Create a new substrate batch."""
        try:
            # Validate component ratios sum to 100%
            total_ratio = sum(comp.ratio_percentage for comp in batch_data.components)
            if abs(total_ratio - 100.0) > 0.01:  # Allow small floating point errors
                logger.warning(f"Component ratios sum to {total_ratio}%, not 100%")
                return None
            
            # Create database model
            db_batch = SubstrateBatchDB(
                farm_id=batch_data.farm_id,
                batch_name=batch_data.batch_name,
                batch_number=batch_data.batch_number,
                description=batch_data.description,
                total_weight=batch_data.total_weight,
                weight_unit=batch_data.weight_unit,
                storage_location=batch_data.storage_location,
                status=batch_data.status
            )
            
            # Add to session
            self.session.add(db_batch)
            await self.session.flush()  # Get ID without committing
            
            # Create batch components
            for component in batch_data.components:
                # Validate substrate_type_id
                if not component.substrate_type_id:
                    logger.error(f"Component missing substrate_type_id")
                    await self.session.rollback()
                    return None
                
                # Calculate weight from ratio
                component_weight = (component.ratio_percentage / 100.0) * batch_data.total_weight
                
                db_component = SubstrateBatchComponentDB(
                    substrate_batch_id=db_batch.id,
                    substrate_type_id=component.substrate_type_id,
                    ratio_percentage=component.ratio_percentage,
                    weight=component_weight
                )
                self.session.add(db_component)
            
            await self.session.commit()
            await self.session.refresh(db_batch)
            
            logger.info(f"Created substrate batch: {db_batch.id}")
            
            # Convert to response model
            return await self._to_substrate_batch_response(db_batch)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating substrate batch: {e}")
            return None
    
    async def get_substrate_batch(self, batch_id: str) -> Optional[SubstrateBatchResponse]:
        """Get a substrate batch by ID."""
        try:
            # Query database with components and substrate types
            result = await self.session.execute(
                select(SubstrateBatchDB)
                .options(
                    selectinload(SubstrateBatchDB.components).selectinload(SubstrateBatchComponentDB.substrate_type),
                    selectinload(SubstrateBatchDB.sensor_devices)
                )
                .where(SubstrateBatchDB.id == batch_id)
            )
            db_batch = result.scalar_one_or_none()
            
            if not db_batch:
                return None
            
            return await self._to_substrate_batch_response(db_batch)
            
        except Exception as e:
            logger.error(f"Error getting substrate batch {batch_id}: {e}")
            return None
    
    async def get_substrate_batches_by_farm(self, farm_id: str, status: Optional[str] = None) -> List[SubstrateBatchResponse]:
        """Get substrate batches for a specific farm."""
        try:
            # Build query
            query = select(SubstrateBatchDB).options(
                selectinload(SubstrateBatchDB.components).selectinload(SubstrateBatchComponentDB.substrate_type),
                selectinload(SubstrateBatchDB.sensor_devices)
            ).where(SubstrateBatchDB.farm_id == farm_id)
            
            if status:
                query = query.where(SubstrateBatchDB.status == status)
            
            query = query.order_by(SubstrateBatchDB.created_at.desc())
            
            # Execute query
            result = await self.session.execute(query)
            db_batches = result.scalars().all()
            
            # Convert to response models
            batches = []
            for db_batch in db_batches:
                response = await self._to_substrate_batch_response(db_batch)
                if response:
                    batches.append(response)
            
            return batches
            
        except Exception as e:
            logger.error(f"Error getting substrate batches for farm {farm_id}: {e}")
            return []
    
    async def update_substrate_batch(self, batch_id: str, batch_data: SubstrateBatchCreate) -> Optional[SubstrateBatchResponse]:
        """Update a substrate batch."""
        try:
            # Validate component ratios sum to 100%
            total_ratio = sum(comp.ratio_percentage for comp in batch_data.components)
            if abs(total_ratio - 100.0) > 0.01:
                logger.warning(f"Component ratios sum to {total_ratio}%, not 100%")
                return None
            
            # Get existing batch
            result = await self.session.execute(
                select(SubstrateBatchDB)
                .options(selectinload(SubstrateBatchDB.components))
                .where(SubstrateBatchDB.id == batch_id)
            )
            db_batch = result.scalar_one_or_none()
            
            if not db_batch:
                return None
            
            # Update batch fields
            setattr(db_batch, 'farm_id', batch_data.farm_id)
            setattr(db_batch, 'batch_name', batch_data.batch_name)
            setattr(db_batch, 'batch_number', batch_data.batch_number)
            setattr(db_batch, 'description', batch_data.description)
            setattr(db_batch, 'total_weight', batch_data.total_weight)
            setattr(db_batch, 'weight_unit', batch_data.weight_unit)
            setattr(db_batch, 'storage_location', batch_data.storage_location)
            setattr(db_batch, 'status', batch_data.status)
            setattr(db_batch, 'updated_at', datetime.now(timezone.utc))
            
            # Delete existing components
            await self.session.execute(
                delete(SubstrateBatchComponentDB).where(
                    SubstrateBatchComponentDB.substrate_batch_id == batch_id
                )
            )
            
            # Create new components
            for component in batch_data.components:
                # Validate substrate_type_id
                if not component.substrate_type_id:
                    logger.error(f"Component missing substrate_type_id")
                    await self.session.rollback()
                    return None
                
                component_weight = (component.ratio_percentage / 100.0) * batch_data.total_weight
                
                db_component = SubstrateBatchComponentDB(
                    substrate_batch_id=db_batch.id,
                    substrate_type_id=component.substrate_type_id,
                    ratio_percentage=component.ratio_percentage,
                    weight=component_weight
                )
                self.session.add(db_component)
            
            await self.session.commit()
            await self.session.refresh(db_batch)
            
            logger.info(f"Updated substrate batch: {batch_id}")
            
            return await self._to_substrate_batch_response(db_batch)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating substrate batch {batch_id}: {e}")
            return None
    
    async def delete_substrate_batch(self, batch_id: str) -> bool:
        """Delete a substrate batch."""
        try:
            # Delete components first (cascade should handle this, but explicit is better)
            await self.session.execute(
                delete(SubstrateBatchComponentDB).where(
                    SubstrateBatchComponentDB.substrate_batch_id == batch_id
                )
            )
            
            # Delete the batch
            await self.session.execute(
                delete(SubstrateBatchDB).where(SubstrateBatchDB.id == batch_id)
            )
            
            await self.session.commit()
            
            logger.info(f"Deleted substrate batch: {batch_id}")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting substrate batch {batch_id}: {e}")
            return False
    
    # Helper methods
    
    async def _to_substrate_type_response(self, db_type: SubstrateTypeDB) -> Optional[SubstrateTypeResponse]:
        """Convert database model to response model."""
        try:
            # Parse custom attributes from JSON
            custom_attributes = None
            custom_attributes_raw = getattr(db_type, 'custom_attributes')
            if custom_attributes_raw:
                custom_attributes = json.loads(custom_attributes_raw)
            
            return SubstrateTypeResponse(
                id=str(getattr(db_type, 'id')),
                name=getattr(db_type, 'name'),
                category=getattr(db_type, 'category'),
                description=getattr(db_type, 'description'),
                custom_attributes=custom_attributes,
                created_at=getattr(db_type, 'created_at'),
                updated_at=getattr(db_type, 'updated_at')
            )
        except Exception as e:
            logger.error(f"Error converting substrate type to response: {e}")
            return None
    
    async def _to_substrate_batch_response(self, db_batch: SubstrateBatchDB) -> Optional[SubstrateBatchResponse]:
        """Convert database model to response model."""
        try:
            # Convert components
            components = []
            batch_components = getattr(db_batch, 'components', [])
            for db_component in batch_components:
                substrate_type = getattr(db_component, 'substrate_type', None)
                
                # Get substrate_type_id safely - skip if None
                substrate_type_id = getattr(db_component, 'substrate_type_id')
                if substrate_type_id is None:
                    logger.warning(f"Component has no substrate_type_id, skipping")
                    continue
                
                component = SubstrateComponent(
                    substrate_type_id=str(substrate_type_id),
                    substrate_type_name=getattr(substrate_type, 'name', 'Unknown') if substrate_type else "Unknown",
                    ratio_percentage=getattr(db_component, 'ratio_percentage'),
                    weight=getattr(db_component, 'weight')
                )
                components.append(component)
            
            # Get associated sensor device IDs
            sensor_devices = getattr(db_batch, 'sensor_devices', [])
            sensor_device_ids = [str(getattr(device, 'id')) for device in sensor_devices] if sensor_devices else []
            
            return SubstrateBatchResponse(
                id=str(getattr(db_batch, 'id')),
                farm_id=getattr(db_batch, 'farm_id'),
                batch_name=getattr(db_batch, 'batch_name'),
                batch_number=getattr(db_batch, 'batch_number'),
                description=getattr(db_batch, 'description'),
                total_weight=getattr(db_batch, 'total_weight'),
                weight_unit=getattr(db_batch, 'weight_unit'),
                storage_location=getattr(db_batch, 'storage_location'),
                status=getattr(db_batch, 'status'),
                components=components,
                sensor_device_ids=sensor_device_ids,
                created_at=getattr(db_batch, 'created_at'),
                updated_at=getattr(db_batch, 'updated_at')
            )
        except Exception as e:
            logger.error(f"Error converting substrate batch to response: {e}")
            return None


# Dependency injection helper
async def get_substrate_repository() -> AsyncGenerator[SubstrateRepository, None]:
    """Get substrate repository with database session."""
    async for session in get_async_session():
        yield SubstrateRepository(session)
