"""
Real-time alert management system.
Monitors sensor data for threshold violations and sends instant notifications.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.websocket.manager import websocket_manager, WebSocketMessage, MessageType
from src.realtime.sensor_streamer import SensorDataPoint
from src.sensors.device_repository import SensorDeviceRepository
from src.database.postgresql import get_async_session
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass
class AlertRule:
    """Alert rule definition."""
    id: str
    name: str
    farm_id: Optional[str]
    device_id: Optional[str]
    measurement_type: str
    min_threshold: Optional[float]
    max_threshold: Optional[float]
    severity: AlertSeverity
    is_active: bool = True
    cooldown_minutes: int = 5
    description: Optional[str] = None


@dataclass
class Alert:
    """Alert instance."""
    id: str
    rule_id: str
    farm_id: str
    device_id: str
    measurement_type: str
    severity: AlertSeverity
    status: AlertStatus
    threshold_value: float
    actual_value: float
    unit: str
    message: str
    created_at: datetime
    updated_at: datetime
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class RealTimeAlertManager:
    """Manages real-time alert generation and notification."""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.is_running = False
        self.monitoring_tasks = []
        
        # Cooldown tracking to prevent alert spam
        self.cooldown_tracker: Dict[str, datetime] = {}
        
        # Statistics
        self.stats = {
            "total_alerts": 0,
            "active_alerts": 0,
            "alerts_sent": 0,
            "rules_evaluated": 0,
            "start_time": None
        }
    
    async def start_monitoring(self):
        """Start real-time alert monitoring."""
        if self.is_running:
            logger.warning("Alert monitoring is already running")
            return
        
        try:
            self.is_running = True
            self.stats["start_time"] = datetime.utcnow()
            
            # Load alert rules from database
            await self.load_alert_rules()
            
            # Start monitoring tasks
            self.monitoring_tasks = [
                asyncio.create_task(self._cleanup_resolved_alerts()),
                asyncio.create_task(self._send_periodic_summaries())
            ]
            
            logger.info("Real-time alert monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start alert monitoring: {e}")
            self.is_running = False
            raise
    
    async def stop_monitoring(self):
        """Stop real-time alert monitoring."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # Cancel monitoring tasks
            for task in self.monitoring_tasks:
                task.cancel()
            
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            self.monitoring_tasks.clear()
            
            logger.info("Real-time alert monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping alert monitoring: {e}")
    
    async def load_alert_rules(self):
        """Load alert rules from the database."""
        try:
            async with get_async_session() as session:
                device_repo = SensorDeviceRepository(session)
                
                # Get alert rules from database
                db_rules = await device_repo.get_alert_rules()
                
                # Convert to internal format
                for db_rule in db_rules:
                    rule = AlertRule(
                        id=db_rule.id,
                        name=db_rule.name,
                        farm_id=db_rule.farm_id,
                        device_id=db_rule.device_id,
                        measurement_type=db_rule.measurement_type,
                        min_threshold=db_rule.min_threshold,
                        max_threshold=db_rule.max_threshold,
                        severity=AlertSeverity(db_rule.severity),
                        is_active=db_rule.is_active,
                        description=db_rule.description
                    )
                    self.alert_rules[rule.id] = rule
                
                logger.info(f"Loaded {len(self.alert_rules)} alert rules")
                
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")
    
    async def evaluate_sensor_data(self, data_point: SensorDataPoint):
        """Evaluate sensor data against alert rules."""
        try:
            self.stats["rules_evaluated"] += 1
            
            # Find applicable rules
            applicable_rules = self._find_applicable_rules(data_point)
            
            for rule in applicable_rules:
                await self._check_threshold_violation(rule, data_point)
                
        except Exception as e:
            logger.error(f"Error evaluating sensor data for alerts: {e}")
    
    def _find_applicable_rules(self, data_point: SensorDataPoint) -> List[AlertRule]:
        """Find alert rules applicable to the sensor data point."""
        applicable_rules = []
        
        for rule in self.alert_rules.values():
            if not rule.is_active:
                continue
            
            # Check if rule applies to this measurement type
            if rule.measurement_type != data_point.measurement_type:
                continue
            
            # Check farm filter
            if rule.farm_id and rule.farm_id != data_point.farm_id:
                continue
            
            # Check device filter
            if rule.device_id and rule.device_id != data_point.device_id:
                continue
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    async def _check_threshold_violation(self, rule: AlertRule, data_point: SensorDataPoint):
        """Check if sensor data violates threshold and create alert if needed."""
        try:
            violation_detected = False
            violation_type = None
            threshold_value = None
            
            # Check high threshold
            if rule.max_threshold is not None and data_point.value > rule.max_threshold:
                violation_detected = True
                violation_type = "high"
                threshold_value = rule.max_threshold
            
            # Check low threshold
            elif rule.min_threshold is not None and data_point.value < rule.min_threshold:
                violation_detected = True
                violation_type = "low"
                threshold_value = rule.min_threshold
            
            if violation_detected:
                await self._create_alert(rule, data_point, violation_type, threshold_value)
            else:
                # Check if we need to resolve any existing alerts
                await self._check_alert_resolution(rule, data_point)
                
        except Exception as e:
            logger.error(f"Error checking threshold violation: {e}")
    
    async def _create_alert(
        self,
        rule: AlertRule,
        data_point: SensorDataPoint,
        violation_type: str,
        threshold_value: float
    ):
        """Create new alert for threshold violation."""
        try:
            # Check cooldown to prevent spam
            cooldown_key = f"{rule.id}_{data_point.device_id}_{violation_type}"
            
            if cooldown_key in self.cooldown_tracker:
                last_alert = self.cooldown_tracker[cooldown_key]
                if (datetime.utcnow() - last_alert).total_seconds() < rule.cooldown_minutes * 60:
                    return  # Still in cooldown
            
            # Create alert
            alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{data_point.device_id}_{violation_type}"
            
            message = (
                f"{rule.name}: {data_point.measurement_type} {violation_type} threshold violation. "
                f"Value: {data_point.value} {data_point.unit}, "
                f"Threshold: {threshold_value} {data_point.unit}"
            )
            
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                farm_id=data_point.farm_id,
                device_id=data_point.device_id,
                measurement_type=data_point.measurement_type,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                threshold_value=threshold_value,
                actual_value=data_point.value,
                unit=data_point.unit,
                message=message,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={
                    "violation_type": violation_type,
                    "rule_name": rule.name,
                    "location": data_point.location,
                    "substrate_batch_id": data_point.substrate_batch_id
                }
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Update cooldown
            self.cooldown_tracker[cooldown_key] = datetime.utcnow()
            
            # Update statistics
            self.stats["total_alerts"] += 1
            self.stats["active_alerts"] = len(self.active_alerts)
            
            # Send alert notification
            await self._send_alert_notification(alert)
            
            logger.warning(f"Alert created: {alert.message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _send_alert_notification(self, alert: Alert):
        """Send alert notification via WebSocket."""
        try:
            # Prepare alert data for WebSocket
            alert_data = {
                "id": alert.id,
                "rule_id": alert.rule_id,
                "farm_id": alert.farm_id,
                "device_id": alert.device_id,
                "measurement_type": alert.measurement_type,
                "severity": alert.severity,
                "status": alert.status,
                "threshold_value": alert.threshold_value,
                "actual_value": alert.actual_value,
                "unit": alert.unit,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            }
            
            # Create WebSocket message
            message = WebSocketMessage(
                message_type=MessageType.ALERT,
                data=alert_data,
                farm_id=alert.farm_id,
                device_id=alert.device_id
            )
            
            # Broadcast alert to interested clients
            await websocket_manager.broadcast_to_farm(alert.farm_id, message)
            await websocket_manager.broadcast_to_device(alert.device_id, message)
            
            # Send to all clients for critical alerts
            if alert.severity == AlertSeverity.CRITICAL:
                await websocket_manager.broadcast_to_all(message)
            
            self.stats["alerts_sent"] += 1
            
            logger.info(f"Alert notification sent: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    async def _check_alert_resolution(self, rule: AlertRule, data_point: SensorDataPoint):
        """Check if any active alerts should be resolved."""
        try:
            # Find active alerts for this rule and device
            alerts_to_resolve = []
            
            for alert in self.active_alerts.values():
                if (alert.rule_id == rule.id and 
                    alert.device_id == data_point.device_id and 
                    alert.status == AlertStatus.ACTIVE):
                    
                    # Check if value is back within thresholds
                    within_thresholds = True
                    
                    if rule.max_threshold is not None and data_point.value > rule.max_threshold:
                        within_thresholds = False
                    
                    if rule.min_threshold is not None and data_point.value < rule.min_threshold:
                        within_thresholds = False
                    
                    if within_thresholds:
                        alerts_to_resolve.append(alert)
            
            # Resolve alerts
            for alert in alerts_to_resolve:
                await self._resolve_alert(alert.id, "automatic", "Value returned to normal range")
                
        except Exception as e:
            logger.error(f"Error checking alert resolution: {e}")
    
    async def _resolve_alert(self, alert_id: str, resolved_by: str, reason: str):
        """Resolve an active alert."""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.updated_at = datetime.utcnow()
                
                if not alert.metadata:
                    alert.metadata = {}
                alert.metadata.update({
                    "resolved_by": resolved_by,
                    "resolution_reason": reason
                })
                
                # Remove from active alerts
                del self.active_alerts[alert_id]
                
                # Update statistics
                self.stats["active_alerts"] = len(self.active_alerts)
                
                # Send resolution notification
                await self._send_alert_notification(alert)
                
                logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
                
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert."""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                alert.updated_at = datetime.utcnow()
                
                # Send acknowledgment notification
                await self._send_alert_notification(alert)
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    async def _cleanup_resolved_alerts(self):
        """Clean up old resolved alerts from memory."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                cleanup_threshold = current_time - timedelta(hours=24)
                
                # Remove old alerts from history
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.created_at > cleanup_threshold
                ]
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error during alert cleanup: {e}")
                await asyncio.sleep(600)  # Back off on error
    
    async def _send_periodic_summaries(self):
        """Send periodic alert summaries to WebSocket clients."""
        while self.is_running:
            try:
                # Send summary every 5 minutes
                await asyncio.sleep(300)
                
                if self.active_alerts:
                    summary_data = {
                        "total_active_alerts": len(self.active_alerts),
                        "critical_alerts": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]),
                        "error_alerts": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.ERROR]),
                        "warning_alerts": len([a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING]),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    message = WebSocketMessage(
                        message_type=MessageType.SYSTEM_STATUS,
                        data={"alert_summary": summary_data}
                    )
                    
                    await websocket_manager.broadcast_to_all(message)
                
            except Exception as e:
                logger.error(f"Error sending alert summary: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics."""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()
        
        return {
            **self.stats,
            "is_running": self.is_running,
            "loaded_rules": len(self.alert_rules),
            "cooldown_entries": len(self.cooldown_tracker),
            "uptime_seconds": uptime
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [
            {
                "id": alert.id,
                "farm_id": alert.farm_id,
                "device_id": alert.device_id,
                "severity": alert.severity,
                "status": alert.status,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "metadata": alert.metadata
            }
            for alert in self.active_alerts.values()
        ]


# Global alert manager instance
alert_manager = RealTimeAlertManager()