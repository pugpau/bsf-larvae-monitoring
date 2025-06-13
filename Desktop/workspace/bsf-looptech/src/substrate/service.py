"""
Service for substrate management operations using PostgreSQL.
This service provides business logic for substrate types and batches.
"""

import logging
from typing import List, Optional, Dict, Any
# datetime and AsyncSession imports removed as not used

from src.substrate.models import (
    SubstrateTypeCreate, SubstrateBatchCreate, SubstrateComponentCreate,
    SubstrateTypeResponse, SubstrateBatchResponse
)
from src.substrate.repository import SubstrateRepository
# settings import removed as not used

logger = logging.getLogger(__name__)


class SubstrateService:
    """Service for substrate management operations."""
    
    def __init__(self, repository: SubstrateRepository):
        self.repository = repository
    
    # Substrate Type Operations
    
    async def create_substrate_type(
        self,
        name: str,
        category: str,
        description: Optional[str] = None,
        custom_attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[SubstrateTypeResponse]:
        """Create a new substrate type."""
        try:
            # Create substrate type data
            substrate_type_data = SubstrateTypeCreate(
                name=name,
                category=category,
                description=description,
                custom_attributes=custom_attributes
            )
            
            # Save to repository
            result = await self.repository.create_substrate_type(substrate_type_data)
            
            if result:
                logger.info(f"Created substrate type: {result.name}")
                return result
            else:
                logger.error("Failed to create substrate type")
                return None
                
        except Exception as e:
            logger.error(f"Error creating substrate type: {e}")
            return None
    
    async def get_substrate_type(self, substrate_type_id: str) -> Optional[SubstrateTypeResponse]:
        """Get a substrate type by ID."""
        try:
            return await self.repository.get_substrate_type(substrate_type_id)
        except Exception as e:
            logger.error(f"Error getting substrate type {substrate_type_id}: {e}")
            return None
    
    async def get_all_substrate_types(self) -> List[SubstrateTypeResponse]:
        """Get all substrate types."""
        try:
            return await self.repository.get_all_substrate_types()
        except Exception as e:
            logger.error(f"Error getting all substrate types: {e}")
            return []
    
    async def update_substrate_type(
        self,
        substrate_type_id: str,
        name: str,
        category: str,
        description: Optional[str] = None,
        custom_attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[SubstrateTypeResponse]:
        """Update an existing substrate type."""
        try:
            # Create update data
            substrate_type_data = SubstrateTypeCreate(
                name=name,
                category=category,
                description=description,
                custom_attributes=custom_attributes
            )
            
            # Update in repository
            result = await self.repository.update_substrate_type(substrate_type_id, substrate_type_data)
            
            if result:
                logger.info(f"Updated substrate type: {substrate_type_id}")
                return result
            else:
                logger.error(f"Failed to update substrate type: {substrate_type_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating substrate type {substrate_type_id}: {e}")
            return None
    
    async def delete_substrate_type(self, substrate_type_id: str) -> bool:
        """Delete a substrate type."""
        try:
            success = await self.repository.delete_substrate_type(substrate_type_id)
            
            if success:
                logger.info(f"Deleted substrate type: {substrate_type_id}")
            else:
                logger.warning(f"Failed to delete substrate type: {substrate_type_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting substrate type {substrate_type_id}: {e}")
            return False
    
    # Substrate Batch Operations
    
    async def create_substrate_batch(
        self,
        farm_id: str,
        batch_name: str,
        components: List[Dict[str, Any]],
        batch_number: Optional[str] = None,
        description: Optional[str] = None,
        total_weight: float = 0.0,
        weight_unit: str = "kg",
        storage_location: Optional[str] = None,
        status: str = "active"
    ) -> Optional[SubstrateBatchResponse]:
        """Create a new substrate batch."""
        try:
            # Validate components
            if not components:
                logger.error("Cannot create batch with empty components")
                return None
            
            # Convert components to proper format
            substrate_components = []
            for comp in components:
                # Handle both dict and object formats
                if isinstance(comp, dict):
                    substrate_type_id = comp.get("substrate_type_id")
                    if not substrate_type_id:
                        logger.error(f"Component missing substrate_type_id: {comp}")
                        return None
                    
                    substrate_components.append(SubstrateComponentCreate(
                        substrate_type_id=substrate_type_id,
                        ratio_percentage=float(comp.get("ratio", comp.get("ratio_percentage", 0)))
                    ))
                else:
                    if not hasattr(comp, 'substrate_type_id') or not comp.substrate_type_id:
                        logger.error(f"Component missing substrate_type_id: {comp}")
                        return None
                    
                    substrate_components.append(SubstrateComponentCreate(
                        substrate_type_id=comp.substrate_type_id,
                        ratio_percentage=float(comp.ratio if hasattr(comp, 'ratio') else comp.ratio_percentage)
                    ))
            
            # Create batch data
            batch_data = SubstrateBatchCreate(
                farm_id=farm_id,
                batch_name=batch_name,
                batch_number=batch_number,
                description=description,
                total_weight=total_weight,
                weight_unit=weight_unit,
                storage_location=storage_location,
                status=status,
                components=substrate_components
            )
            
            # Save to repository
            result = await self.repository.create_substrate_batch(batch_data)
            
            if result:
                logger.info(f"Created substrate batch: {result.batch_name}")
                return result
            else:
                logger.error("Failed to create substrate batch")
                return None
                
        except Exception as e:
            logger.error(f"Error creating substrate batch: {e}")
            return None
    
    async def get_substrate_batch(self, batch_id: str) -> Optional[SubstrateBatchResponse]:
        """Get a substrate batch by ID."""
        try:
            return await self.repository.get_substrate_batch(batch_id)
        except Exception as e:
            logger.error(f"Error getting substrate batch {batch_id}: {e}")
            return None
    
    async def get_active_batches_by_farm(self, farm_id: str) -> List[SubstrateBatchResponse]:
        """Get all active substrate batches for a farm."""
        try:
            return await self.repository.get_substrate_batches_by_farm(farm_id, status="active")
        except Exception as e:
            logger.error(f"Error getting active batches for farm {farm_id}: {e}")
            return []
    
    async def get_all_batches_by_farm(self, farm_id: str) -> List[SubstrateBatchResponse]:
        """Get all substrate batches for a farm."""
        try:
            return await self.repository.get_substrate_batches_by_farm(farm_id)
        except Exception as e:
            logger.error(f"Error getting all batches for farm {farm_id}: {e}")
            return []
    
    async def update_substrate_batch(
        self,
        batch_id: str,
        farm_id: str,
        batch_name: str,
        components: List[Dict[str, Any]],
        batch_number: Optional[str] = None,
        description: Optional[str] = None,
        total_weight: float = 0.0,
        weight_unit: str = "kg",
        storage_location: Optional[str] = None,
        status: str = "active"
    ) -> Optional[SubstrateBatchResponse]:
        """Update an existing substrate batch."""
        try:
            # Get current batch to verify it exists
            current_batch = await self.repository.get_substrate_batch(batch_id)
            if not current_batch:
                logger.error(f"Batch not found for update: {batch_id}")
                return None
            
            # Convert components to proper format
            substrate_components = []
            for comp in components:
                if isinstance(comp, dict):
                    substrate_type_id = comp.get("substrate_type_id")
                    if not substrate_type_id:
                        logger.error(f"Component missing substrate_type_id: {comp}")
                        return None
                    
                    substrate_components.append(SubstrateComponentCreate(
                        substrate_type_id=substrate_type_id,
                        ratio_percentage=float(comp.get("ratio", comp.get("ratio_percentage", 0)))
                    ))
                else:
                    if not hasattr(comp, 'substrate_type_id') or not comp.substrate_type_id:
                        logger.error(f"Component missing substrate_type_id: {comp}")
                        return None
                    
                    substrate_components.append(SubstrateComponentCreate(
                        substrate_type_id=comp.substrate_type_id,
                        ratio_percentage=float(comp.ratio if hasattr(comp, 'ratio') else comp.ratio_percentage)
                    ))
            
            # Create update data
            batch_data = SubstrateBatchCreate(
                farm_id=farm_id,
                batch_name=batch_name,
                batch_number=batch_number,
                description=description,
                total_weight=total_weight,
                weight_unit=weight_unit,
                storage_location=storage_location,
                status=status,
                components=substrate_components
            )
            
            # Update in repository
            result = await self.repository.update_substrate_batch(batch_id, batch_data)
            
            if result:
                logger.info(f"Updated substrate batch: {batch_id}")
                return result
            else:
                logger.error(f"Failed to update substrate batch: {batch_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating substrate batch {batch_id}: {e}")
            return None
    
    async def update_batch_status(
        self,
        batch_id: str,
        new_status: str,
        change_reason: Optional[str] = None,
        changed_by: Optional[str] = None
    ) -> bool:
        """Update the status of a substrate batch."""
        try:
            # TODO: Use change_reason and changed_by for audit logging in future
            # Currently these parameters are reserved for future implementation
            _ = (change_reason, changed_by)  # Acknowledge unused parameters
            
            # Get current batch
            batch = await self.repository.get_substrate_batch(batch_id)
            if not batch:
                logger.error(f"Batch not found for status update: {batch_id}")
                return False
            
            # Create update data with current values but new status
            batch_data = SubstrateBatchCreate(
                farm_id=batch.farm_id,
                batch_name=batch.batch_name,
                batch_number=batch.batch_number,
                description=batch.description,
                total_weight=batch.total_weight,
                weight_unit=batch.weight_unit,
                storage_location=batch.storage_location,
                status=new_status,
                components=[
                    SubstrateComponentCreate(
                        substrate_type_id=comp.substrate_type_id,
                        ratio_percentage=comp.ratio_percentage
                    ) for comp in batch.components
                ]
            )
            
            # Update in repository
            result = await self.repository.update_substrate_batch(batch_id, batch_data)
            
            if result:
                logger.info(f"Updated batch status to {new_status}: {batch_id}")
                # TODO: Create change log if needed
                return True
            else:
                logger.error(f"Failed to update batch status: {batch_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating batch status {batch_id}: {e}")
            return False
    
    async def delete_substrate_batch(self, batch_id: str) -> bool:
        """Delete a substrate batch."""
        try:
            success = await self.repository.delete_substrate_batch(batch_id)
            
            if success:
                logger.info(f"Deleted substrate batch: {batch_id}")
            else:
                logger.warning(f"Failed to delete substrate batch: {batch_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting substrate batch {batch_id}: {e}")
            return False
    
    # Note: Change history functionality can be implemented later
    async def get_batch_change_history(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get the change history for a substrate batch."""
        # TODO: Implement change history functionality
        _ = batch_id  # Acknowledge unused parameter - will be used in future implementation
        logger.warning("Change history functionality not yet implemented")
        return []