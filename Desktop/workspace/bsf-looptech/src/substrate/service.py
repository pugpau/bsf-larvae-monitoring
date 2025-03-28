"""
Service for substrate management operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.substrate.models import SubstrateType, SubstrateBatch, SubstrateChangeLog, SubstrateTypeEnum
from src.substrate.repository import SubstrateRepository
from src.config import settings

logger = logging.getLogger(__name__)

class SubstrateService:
    """Service for substrate management operations."""
    
    def __init__(self):
        self.repository = SubstrateRepository()
    
    # Substrate Type Operations
    
    def create_substrate_type(self, name: str, type_enum: SubstrateTypeEnum, 
                             description: Optional[str] = None, 
                             attributes: Optional[List[Dict[str, Any]]] = None) -> Optional[SubstrateType]:
        """Create a new substrate type."""
        try:
            substrate_type = SubstrateType(
                name=name,
                type=type_enum,
                description=description,
                attributes=attributes or []
            )
            
            success = self.repository.save_substrate_type(substrate_type)
            if success:
                logger.info(f"Created substrate type: {substrate_type.id}")
                return substrate_type
            else:
                logger.error("Failed to save substrate type")
                return None
        except Exception as e:
            logger.error(f"Error creating substrate type: {e}")
            return None
    
    def get_substrate_type(self, substrate_type_id: str) -> Optional[SubstrateType]:
        """Get a substrate type by ID."""
        return self.repository.get_substrate_type(substrate_type_id)
    
    def get_all_substrate_types(self) -> List[SubstrateType]:
        """Get all substrate types."""
        return self.repository.get_all_substrate_types()
    
    def update_substrate_type(self, substrate_type: SubstrateType) -> bool:
        """Update an existing substrate type."""
        try:
            # Update the timestamp
            substrate_type.updated_at = datetime.utcnow()
            
            success = self.repository.save_substrate_type(substrate_type)
            if success:
                logger.info(f"Updated substrate type: {substrate_type.id}")
                return True
            else:
                logger.error(f"Failed to update substrate type: {substrate_type.id}")
                return False
        except Exception as e:
            logger.error(f"Error updating substrate type: {e}")
            return False
    
    # Substrate Batch Operations
    
    def create_substrate_batch(self, farm_id: str, components: List[Dict[str, Any]], 
                              name: Optional[str] = None, description: Optional[str] = None,
                              total_weight: Optional[float] = None, 
                              weight_unit: Optional[str] = "kg",
                              batch_number: Optional[str] = None,
                              location: Optional[str] = None,
                              attributes: Optional[List[Dict[str, Any]]] = None) -> Optional[SubstrateBatch]:
        """Create a new substrate batch."""
        try:
            # Validate components
            if not components:
                logger.error("Cannot create batch with empty components")
                return None
            
            # Create batch
            batch = SubstrateBatch(
                farm_id=farm_id,
                name=name,
                description=description,
                components=components,
                total_weight=total_weight,
                weight_unit=weight_unit,
                batch_number=batch_number,
                location=location,
                attributes=attributes or []
            )
            
            # Save batch
            success = self.repository.save_substrate_batch(batch)
            if not success:
                logger.error("Failed to save substrate batch")
                return None
            
            # Create change log
            self._create_change_log(
                batch_id=batch.id,
                change_type="created",
                previous_state=None,
                new_state=batch.dict(),
                change_reason="Initial batch creation"
            )
            
            logger.info(f"Created substrate batch: {batch.id}")
            return batch
        except Exception as e:
            logger.error(f"Error creating substrate batch: {e}")
            return None
    
    def get_substrate_batch(self, batch_id: str) -> Optional[SubstrateBatch]:
        """Get a substrate batch by ID."""
        return self.repository.get_substrate_batch(batch_id)
    
    def get_active_batches_by_farm(self, farm_id: str) -> List[SubstrateBatch]:
        """Get all active substrate batches for a farm."""
        return self.repository.get_substrate_batches_by_farm(farm_id, status="active")
    
    def get_all_batches_by_farm(self, farm_id: str) -> List[SubstrateBatch]:
        """Get all substrate batches for a farm."""
        return self.repository.get_substrate_batches_by_farm(farm_id)
    
    def update_substrate_batch(self, batch: SubstrateBatch, 
                              change_reason: Optional[str] = None,
                              changed_by: Optional[str] = None) -> bool:
        """Update an existing substrate batch."""
        try:
            # Get the current state before updating
            current_batch = self.repository.get_substrate_batch(batch.id)
            if not current_batch:
                logger.error(f"Batch not found for update: {batch.id}")
                return False
            
            # Store the previous state for change log
            previous_state = current_batch.dict()
            
            # Update timestamp
            batch.updated_at = datetime.utcnow()
            
            # Save updated batch
            success = self.repository.save_substrate_batch(batch)
            if not success:
                logger.error(f"Failed to update substrate batch: {batch.id}")
                return False
            
            # Create change log
            self._create_change_log(
                batch_id=batch.id,
                change_type="updated",
                previous_state=previous_state,
                new_state=batch.dict(),
                change_reason=change_reason or "Batch updated",
                changed_by=changed_by
            )
            
            logger.info(f"Updated substrate batch: {batch.id}")
            return True
        except Exception as e:
            logger.error(f"Error updating substrate batch: {e}")
            return False
    
    def update_batch_status(self, batch_id: str, new_status: str, 
                           change_reason: Optional[str] = None,
                           changed_by: Optional[str] = None) -> bool:
        """Update the status of a substrate batch."""
        try:
            batch = self.repository.get_substrate_batch(batch_id)
            if not batch:
                logger.error(f"Batch not found for status update: {batch_id}")
                return False
            
            # Store previous state
            previous_state = batch.dict()
            
            # Update status
            batch.status = new_status
            batch.updated_at = datetime.utcnow()
            
            # Save updated batch
            success = self.repository.save_substrate_batch(batch)
            if not success:
                logger.error(f"Failed to update batch status: {batch_id}")
                return False
            
            # Create change log
            self._create_change_log(
                batch_id=batch_id,
                change_type="status_changed",
                previous_state={"status": previous_state["status"]},
                new_state={"status": new_status},
                change_reason=change_reason or f"Status changed to {new_status}",
                changed_by=changed_by
            )
            
            logger.info(f"Updated batch status to {new_status}: {batch_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating batch status: {e}")
            return False
    
    def get_batch_change_history(self, batch_id: str) -> List[SubstrateChangeLog]:
        """Get the change history for a substrate batch."""
        return self.repository.get_change_logs_for_batch(batch_id)
    
    # Helper methods
    
    def _create_change_log(self, batch_id: str, change_type: str, 
                          previous_state: Optional[Dict[str, Any]], 
                          new_state: Optional[Dict[str, Any]],
                          change_reason: Optional[str] = None,
                          changed_by: Optional[str] = None) -> bool:
        """Create a change log entry for a substrate batch."""
        try:
            change_log = SubstrateChangeLog(
                batch_id=batch_id,
                change_type=change_type,
                previous_state=previous_state,
                new_state=new_state,
                change_reason=change_reason,
                changed_by=changed_by
            )
            
            return self.repository.save_substrate_change_log(change_log)
        except Exception as e:
            logger.error(f"Error creating change log: {e}")
            return False