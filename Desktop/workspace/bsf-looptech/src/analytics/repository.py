"""
Repository for anomaly detection rules and results.
Handles database operations for analytics system.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from src.analytics.models import (
    AnomalyDetectionRule, AnomalyDetection, 
    RuleStatus, AnomalyStatus, RuleSeverity,
    ThresholdCondition, DynamicThreshold
)
from src.database.postgresql import (
    AnomalyRule as AnomalyRuleDB,
    AnomalyDetection as AnomalyDetectionDB
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnomalyRuleRepository:
    """Repository for anomaly detection rules."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_rule(self, rule: AnomalyDetectionRule) -> Optional[AnomalyDetectionRule]:
        """Create a new anomaly detection rule."""
        try:
            db_rule = AnomalyRuleDB(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                farm_id=rule.farm_id,
                device_id=rule.device_id,
                device_type=rule.device_type,
                conditions=[cond.dict() for cond in rule.conditions],
                condition_logic=rule.condition_logic,
                severity=rule.severity,
                status=rule.status,
                evaluation_window=rule.evaluation_window.dict() if rule.evaluation_window else None,
                cooldown_period=rule.cooldown_period.dict() if rule.cooldown_period else None,
                dynamic_threshold=rule.dynamic_threshold.dict() if rule.dynamic_threshold else None,
                send_alert=rule.send_alert,
                auto_control=rule.auto_control,
                control_commands=rule.control_commands,
                created_by=rule.created_by,
                tags=rule.tags
            )
            
            self.session.add(db_rule)
            await self.session.commit()
            await self.session.refresh(db_rule)
            
            return self._db_to_model(db_rule)
            
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            await self.session.rollback()
            return None
    
    async def get_rule(self, rule_id: UUID) -> Optional[AnomalyDetectionRule]:
        """Get a rule by ID."""
        try:
            result = await self.session.execute(
                select(AnomalyRuleDB).where(AnomalyRuleDB.id == rule_id)
            )
            db_rule = result.scalar_one_or_none()
            
            if db_rule:
                return self._db_to_model(db_rule)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get rule {rule_id}: {e}")
            return None
    
    async def get_all_rules(
        self, 
        status: Optional[RuleStatus] = None,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        severity: Optional[RuleSeverity] = None
    ) -> List[AnomalyDetectionRule]:
        """Get all rules with optional filters."""
        try:
            query = select(AnomalyRuleDB)
            
            # Apply filters
            filters = []
            if status:
                filters.append(AnomalyRuleDB.status == status)
            if farm_id:
                filters.append(AnomalyRuleDB.farm_id == farm_id)
            if device_id:
                filters.append(AnomalyRuleDB.device_id == device_id)
            if severity:
                filters.append(AnomalyRuleDB.severity == severity)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await self.session.execute(query)
            db_rules = result.scalars().all()
            
            return [self._db_to_model(rule) for rule in db_rules]
            
        except Exception as e:
            logger.error(f"Failed to get rules: {e}")
            return []
    
    async def update_rule(self, rule_id: UUID, updates: Dict[str, Any]) -> Optional[AnomalyDetectionRule]:
        """Update a rule."""
        try:
            # Get existing rule
            result = await self.session.execute(
                select(AnomalyRuleDB).where(AnomalyRuleDB.id == rule_id)
            )
            db_rule = result.scalar_one_or_none()
            
            if not db_rule:
                return None
            
            # Update fields
            for key, value in updates.items():
                if hasattr(db_rule, key) and value is not None:
                    if key == "conditions":
                        value = [cond.dict() if hasattr(cond, 'dict') else cond for cond in value]
                    elif key in ["evaluation_window", "cooldown_period", "dynamic_threshold"]:
                        value = value.dict() if hasattr(value, 'dict') else value
                    setattr(db_rule, key, value)
            
            db_rule.updated_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(db_rule)
            
            return self._db_to_model(db_rule)
            
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            await self.session.rollback()
            return None
    
    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a rule."""
        try:
            result = await self.session.execute(
                delete(AnomalyRuleDB).where(AnomalyRuleDB.id == rule_id)
            )
            await self.session.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to delete rule {rule_id}: {e}")
            await self.session.rollback()
            return False
    
    def _db_to_model(self, db_rule: AnomalyRuleDB) -> AnomalyDetectionRule:
        """Convert database model to Pydantic model."""
        return AnomalyDetectionRule(
            id=db_rule.id,
            name=db_rule.name,
            description=db_rule.description,
            farm_id=db_rule.farm_id,
            device_id=db_rule.device_id,
            device_type=db_rule.device_type,
            conditions=[ThresholdCondition(**cond) for cond in db_rule.conditions],
            condition_logic=db_rule.condition_logic,
            severity=db_rule.severity,
            status=db_rule.status,
            evaluation_window=db_rule.evaluation_window,
            cooldown_period=db_rule.cooldown_period,
            dynamic_threshold=DynamicThreshold(**db_rule.dynamic_threshold) if db_rule.dynamic_threshold else None,
            send_alert=db_rule.send_alert,
            auto_control=db_rule.auto_control,
            control_commands=db_rule.control_commands,
            created_at=db_rule.created_at,
            updated_at=db_rule.updated_at,
            created_by=db_rule.created_by,
            tags=db_rule.tags
        )


class AnomalyDetectionRepository:
    """Repository for anomaly detections."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_anomaly(self, anomaly: AnomalyDetection) -> Optional[AnomalyDetection]:
        """Create a new anomaly detection record."""
        try:
            db_anomaly = AnomalyDetectionDB(
                id=anomaly.id,
                rule_id=anomaly.rule_id,
                rule_name=anomaly.rule_name,
                detected_at=anomaly.detected_at,
                measurement_type=anomaly.measurement_type,
                actual_value=anomaly.actual_value,
                threshold_value=anomaly.threshold_value,
                threshold_type=anomaly.threshold_type,
                farm_id=anomaly.farm_id,
                device_id=anomaly.device_id,
                device_type=anomaly.device_type,
                location=anomaly.location,
                severity=anomaly.severity,
                status=anomaly.status,
                sensor_data=anomaly.sensor_data,
                metadata=anomaly.metadata
            )
            
            self.session.add(db_anomaly)
            await self.session.commit()
            await self.session.refresh(db_anomaly)
            
            return self._db_to_model(db_anomaly)
            
        except Exception as e:
            logger.error(f"Failed to create anomaly: {e}")
            await self.session.rollback()
            return None
    
    async def get_anomaly(self, anomaly_id: UUID) -> Optional[AnomalyDetection]:
        """Get an anomaly by ID."""
        try:
            result = await self.session.execute(
                select(AnomalyDetectionDB).where(AnomalyDetectionDB.id == anomaly_id)
            )
            db_anomaly = result.scalar_one_or_none()
            
            if db_anomaly:
                return self._db_to_model(db_anomaly)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get anomaly {anomaly_id}: {e}")
            return None
    
    async def get_anomalies(
        self,
        status: Optional[AnomalyStatus] = None,
        severity: Optional[RuleSeverity] = None,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        rule_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AnomalyDetection]:
        """Get anomalies with filters."""
        try:
            query = select(AnomalyDetectionDB)
            
            # Apply filters
            filters = []
            if status:
                filters.append(AnomalyDetectionDB.status == status)
            if severity:
                filters.append(AnomalyDetectionDB.severity == severity)
            if farm_id:
                filters.append(AnomalyDetectionDB.farm_id == farm_id)
            if device_id:
                filters.append(AnomalyDetectionDB.device_id == device_id)
            if rule_id:
                filters.append(AnomalyDetectionDB.rule_id == rule_id)
            if start_time:
                filters.append(AnomalyDetectionDB.detected_at >= start_time)
            if end_time:
                filters.append(AnomalyDetectionDB.detected_at <= end_time)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Order by detection time (newest first)
            query = query.order_by(AnomalyDetectionDB.detected_at.desc())
            query = query.limit(limit).offset(offset)
            
            result = await self.session.execute(query)
            db_anomalies = result.scalars().all()
            
            return [self._db_to_model(anomaly) for anomaly in db_anomalies]
            
        except Exception as e:
            logger.error(f"Failed to get anomalies: {e}")
            return []
    
    async def update_anomaly_status(
        self,
        anomaly_id: UUID,
        status: AnomalyStatus,
        user: str,
        notes: Optional[str] = None
    ) -> Optional[AnomalyDetection]:
        """Update anomaly status."""
        try:
            # Get existing anomaly
            result = await self.session.execute(
                select(AnomalyDetectionDB).where(AnomalyDetectionDB.id == anomaly_id)
            )
            db_anomaly = result.scalar_one_or_none()
            
            if not db_anomaly:
                return None
            
            # Update status
            db_anomaly.status = status
            
            if status == AnomalyStatus.ACKNOWLEDGED:
                db_anomaly.acknowledged_by = user
                db_anomaly.acknowledged_at = datetime.utcnow()
            elif status == AnomalyStatus.RESOLVED:
                db_anomaly.resolved_by = user
                db_anomaly.resolved_at = datetime.utcnow()
                db_anomaly.resolution_notes = notes
            
            await self.session.commit()
            await self.session.refresh(db_anomaly)
            
            return self._db_to_model(db_anomaly)
            
        except Exception as e:
            logger.error(f"Failed to update anomaly status: {e}")
            await self.session.rollback()
            return None
    
    async def get_anomaly_statistics(
        self,
        farm_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get anomaly statistics."""
        try:
            # Base query
            base_query = select(AnomalyDetectionDB)
            
            # Apply filters
            filters = []
            if farm_id:
                filters.append(AnomalyDetectionDB.farm_id == farm_id)
            if start_time:
                filters.append(AnomalyDetectionDB.detected_at >= start_time)
            if end_time:
                filters.append(AnomalyDetectionDB.detected_at <= end_time)
            
            if filters:
                base_query = base_query.where(and_(*filters))
            
            # Get total count
            total_result = await self.session.execute(
                select(func.count()).select_from(base_query.subquery())
            )
            total_count = total_result.scalar()
            
            # Get counts by status
            status_counts = {}
            for status in AnomalyStatus:
                status_query = base_query.where(AnomalyDetectionDB.status == status)
                result = await self.session.execute(
                    select(func.count()).select_from(status_query.subquery())
                )
                status_counts[status] = result.scalar()
            
            # Get counts by severity
            severity_counts = {}
            for severity in RuleSeverity:
                severity_query = base_query.where(AnomalyDetectionDB.severity == severity)
                result = await self.session.execute(
                    select(func.count()).select_from(severity_query.subquery())
                )
                severity_counts[severity] = result.scalar()
            
            return {
                "total_anomalies": total_count,
                "by_status": status_counts,
                "by_severity": severity_counts,
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get anomaly statistics: {e}")
            return {}
    
    def _db_to_model(self, db_anomaly: AnomalyDetectionDB) -> AnomalyDetection:
        """Convert database model to Pydantic model."""
        return AnomalyDetection(
            id=db_anomaly.id,
            rule_id=db_anomaly.rule_id,
            rule_name=db_anomaly.rule_name,
            detected_at=db_anomaly.detected_at,
            measurement_type=db_anomaly.measurement_type,
            actual_value=db_anomaly.actual_value,
            threshold_value=db_anomaly.threshold_value,
            threshold_type=db_anomaly.threshold_type,
            farm_id=db_anomaly.farm_id,
            device_id=db_anomaly.device_id,
            device_type=db_anomaly.device_type,
            location=db_anomaly.location,
            severity=db_anomaly.severity,
            status=db_anomaly.status,
            acknowledged_by=db_anomaly.acknowledged_by,
            acknowledged_at=db_anomaly.acknowledged_at,
            resolved_by=db_anomaly.resolved_by,
            resolved_at=db_anomaly.resolved_at,
            resolution_notes=db_anomaly.resolution_notes,
            sensor_data=db_anomaly.sensor_data,
            metadata=db_anomaly.metadata
        )