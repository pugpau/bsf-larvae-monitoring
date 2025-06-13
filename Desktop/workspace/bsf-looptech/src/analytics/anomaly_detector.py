"""
Anomaly detection engine for sensor data.
Implements threshold-based and dynamic anomaly detection.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from collections import defaultdict

from src.analytics.models import (
    AnomalyDetectionRule, ThresholdCondition, ThresholdType,
    AnomalyDetection, AnomalyStatus, RuleSeverity, RuleStatus,
    DynamicThreshold, TimeWindow
)
from src.sensors.models import SensorReading
from src.database.influxdb import InfluxDBClient
from src.websocket.manager import websocket_manager, WebSocketMessage, MessageType
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnomalyDetector:
    """Core anomaly detection engine."""
    
    def __init__(self):
        self.rules: Dict[UUID, AnomalyDetectionRule] = {}
        self.active_anomalies: Dict[UUID, AnomalyDetection] = {}
        self.rule_cooldowns: Dict[UUID, datetime] = {}
        self.influx_client = InfluxDBClient()
        self.is_running = False
        self._evaluation_task = None
        
    async def start(self):
        """Start the anomaly detection engine."""
        if self.is_running:
            logger.warning("Anomaly detector is already running")
            return
        
        self.is_running = True
        await self.load_rules()
        self._evaluation_task = asyncio.create_task(self._continuous_evaluation())
        logger.info("Anomaly detection engine started")
    
    async def stop(self):
        """Stop the anomaly detection engine."""
        self.is_running = False
        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
        logger.info("Anomaly detection engine stopped")
    
    async def load_rules(self):
        """Load anomaly detection rules from database."""
        # TODO: Load from PostgreSQL
        logger.info(f"Loaded {len(self.rules)} anomaly detection rules")
    
    async def add_rule(self, rule: AnomalyDetectionRule) -> bool:
        """Add a new anomaly detection rule."""
        try:
            self.rules[rule.id] = rule
            logger.info(f"Added rule: {rule.name} (ID: {rule.id})")
            return True
        except Exception as e:
            logger.error(f"Failed to add rule: {e}")
            return False
    
    async def update_rule(self, rule_id: UUID, rule: AnomalyDetectionRule) -> bool:
        """Update an existing rule."""
        try:
            if rule_id in self.rules:
                self.rules[rule_id] = rule
                logger.info(f"Updated rule: {rule.name} (ID: {rule_id})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update rule: {e}")
            return False
    
    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a rule."""
        try:
            if rule_id in self.rules:
                del self.rules[rule_id]
                if rule_id in self.rule_cooldowns:
                    del self.rule_cooldowns[rule_id]
                logger.info(f"Deleted rule: {rule_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete rule: {e}")
            return False
    
    async def evaluate_reading(self, reading: SensorReading) -> List[AnomalyDetection]:
        """Evaluate a single sensor reading against all applicable rules."""
        anomalies = []
        
        for rule in self.rules.values():
            if rule.status != RuleStatus.ACTIVE:
                continue
            
            # Check if rule applies to this reading
            if not self._rule_applies_to_reading(rule, reading):
                continue
            
            # Check cooldown
            if self._is_in_cooldown(rule.id):
                continue
            
            # Evaluate rule
            anomaly = await self._evaluate_rule(rule, reading)
            if anomaly:
                anomalies.append(anomaly)
                await self._handle_anomaly(anomaly, rule)
        
        return anomalies
    
    def _rule_applies_to_reading(self, rule: AnomalyDetectionRule, reading: SensorReading) -> bool:
        """Check if a rule applies to a specific reading."""
        # Check farm_id
        if rule.farm_id and reading.farm_id != rule.farm_id:
            return False
        
        # Check device_id
        if rule.device_id and reading.device_id != rule.device_id:
            return False
        
        # Check device_type
        if rule.device_type and reading.device_type != rule.device_type:
            return False
        
        # Check if rule has conditions for this measurement type
        measurement_types = {cond.measurement_type for cond in rule.conditions}
        if reading.measurement_type not in measurement_types:
            return False
        
        return True
    
    def _is_in_cooldown(self, rule_id: UUID) -> bool:
        """Check if a rule is in cooldown period."""
        if rule_id not in self.rule_cooldowns:
            return False
        
        cooldown_end = self.rule_cooldowns[rule_id]
        return datetime.utcnow() < cooldown_end
    
    async def _evaluate_rule(
        self, 
        rule: AnomalyDetectionRule, 
        reading: SensorReading
    ) -> Optional[AnomalyDetection]:
        """Evaluate a rule against a sensor reading."""
        try:
            # Get historical data if needed for dynamic thresholds
            historical_data = None
            if rule.dynamic_threshold and rule.dynamic_threshold.enabled:
                historical_data = await self._get_historical_data(
                    rule, reading, rule.dynamic_threshold.learning_window
                )
            
            # Evaluate conditions
            condition_results = []
            triggered_condition = None
            
            for condition in rule.conditions:
                if condition.measurement_type != reading.measurement_type:
                    continue
                
                # Apply dynamic threshold if enabled
                threshold_value = condition.value
                if rule.dynamic_threshold and rule.dynamic_threshold.enabled and historical_data:
                    threshold_value = self._calculate_dynamic_threshold(
                        historical_data, rule.dynamic_threshold, condition
                    )
                
                # Check condition
                is_violated = self._check_threshold_condition(
                    reading.value, threshold_value, condition.threshold_type
                )
                
                condition_results.append(is_violated)
                if is_violated and not triggered_condition:
                    triggered_condition = (condition, threshold_value)
            
            # Apply condition logic
            if not condition_results:
                return None
            
            anomaly_detected = False
            if rule.condition_logic == "AND":
                anomaly_detected = all(condition_results)
            else:  # OR
                anomaly_detected = any(condition_results)
            
            if anomaly_detected and triggered_condition:
                condition, threshold_value = triggered_condition
                
                # Create anomaly detection
                anomaly = AnomalyDetection(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    measurement_type=reading.measurement_type,
                    actual_value=reading.value,
                    threshold_value=threshold_value,
                    threshold_type=condition.threshold_type,
                    farm_id=reading.farm_id,
                    device_id=reading.device_id,
                    device_type=reading.device_type,
                    location=reading.location,
                    severity=rule.severity,
                    sensor_data={
                        "reading_id": str(reading.id),
                        "timestamp": reading.timestamp.isoformat(),
                        "unit": reading.unit
                    }
                )
                
                return anomaly
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.id}: {e}")
            return None
    
    def _check_threshold_condition(
        self, 
        value: float, 
        threshold: Union[float, List[float]], 
        threshold_type: ThresholdType
    ) -> bool:
        """Check if a value violates a threshold condition."""
        if threshold_type == ThresholdType.GREATER_THAN:
            return value > threshold
        elif threshold_type == ThresholdType.LESS_THAN:
            return value < threshold
        elif threshold_type == ThresholdType.EQUAL_TO:
            return value == threshold
        elif threshold_type == ThresholdType.NOT_EQUAL_TO:
            return value != threshold
        elif threshold_type == ThresholdType.BETWEEN:
            return threshold[0] <= value <= threshold[1]
        elif threshold_type == ThresholdType.OUTSIDE_RANGE:
            return value < threshold[0] or value > threshold[1]
        
        return False
    
    async def _get_historical_data(
        self, 
        rule: AnomalyDetectionRule, 
        reading: SensorReading,
        time_window: TimeWindow
    ) -> List[float]:
        """Get historical data for dynamic threshold calculation."""
        try:
            # Calculate time range
            end_time = reading.timestamp
            start_time = end_time - timedelta(seconds=time_window.to_seconds())
            
            # Query InfluxDB
            query = f'''
            from(bucket:"{self.influx_client.bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "sensor_data")
                |> filter(fn: (r) => r["device_id"] == "{reading.device_id}")
                |> filter(fn: (r) => r["measurement_type"] == "{reading.measurement_type}")
                |> filter(fn: (r) => r["_field"] == "value")
                |> yield(name: "historical_data")
            '''
            
            result = self.influx_client.query(query)
            values = []
            
            for table in result:
                for record in table.records:
                    values.append(record.get_value())
            
            return values
            
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return []
    
    def _calculate_dynamic_threshold(
        self,
        historical_data: List[float],
        dynamic_config: DynamicThreshold,
        condition: ThresholdCondition
    ) -> Union[float, List[float]]:
        """Calculate dynamic threshold based on historical data."""
        if not historical_data:
            return condition.value
        
        import numpy as np
        data = np.array(historical_data)
        
        if dynamic_config.method == "stddev":
            # Standard deviation method
            mean = np.mean(data)
            std = np.std(data)
            factor = dynamic_config.parameters.get("factor", 2.0)
            
            if condition.threshold_type == ThresholdType.GREATER_THAN:
                return mean + (factor * std)
            elif condition.threshold_type == ThresholdType.LESS_THAN:
                return mean - (factor * std)
            elif condition.threshold_type in [ThresholdType.BETWEEN, ThresholdType.OUTSIDE_RANGE]:
                return [mean - (factor * std), mean + (factor * std)]
                
        elif dynamic_config.method == "percentile":
            # Percentile method
            lower_percentile = dynamic_config.parameters.get("lower_percentile", 5)
            upper_percentile = dynamic_config.parameters.get("upper_percentile", 95)
            
            if condition.threshold_type == ThresholdType.GREATER_THAN:
                return np.percentile(data, upper_percentile)
            elif condition.threshold_type == ThresholdType.LESS_THAN:
                return np.percentile(data, lower_percentile)
            elif condition.threshold_type in [ThresholdType.BETWEEN, ThresholdType.OUTSIDE_RANGE]:
                return [np.percentile(data, lower_percentile), np.percentile(data, upper_percentile)]
                
        elif dynamic_config.method == "iqr":
            # Interquartile range method
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            factor = dynamic_config.parameters.get("factor", 1.5)
            
            if condition.threshold_type == ThresholdType.GREATER_THAN:
                return q3 + (factor * iqr)
            elif condition.threshold_type == ThresholdType.LESS_THAN:
                return q1 - (factor * iqr)
            elif condition.threshold_type in [ThresholdType.BETWEEN, ThresholdType.OUTSIDE_RANGE]:
                return [q1 - (factor * iqr), q3 + (factor * iqr)]
        
        # Fallback to static threshold
        return condition.value
    
    async def _handle_anomaly(self, anomaly: AnomalyDetection, rule: AnomalyDetectionRule):
        """Handle detected anomaly."""
        try:
            # Store anomaly
            self.active_anomalies[anomaly.id] = anomaly
            
            # Set cooldown
            if rule.cooldown_period:
                cooldown_duration = timedelta(seconds=rule.cooldown_period.to_seconds())
                self.rule_cooldowns[rule.id] = datetime.utcnow() + cooldown_duration
            
            # Send alert if enabled
            if rule.send_alert:
                await self._send_anomaly_alert(anomaly)
            
            # Execute auto-control if enabled
            if rule.auto_control and rule.control_commands:
                await self._execute_control_commands(anomaly, rule.control_commands)
            
            logger.warning(
                f"Anomaly detected: {anomaly.rule_name} - "
                f"{anomaly.measurement_type} = {anomaly.actual_value} "
                f"(threshold: {anomaly.threshold_value})"
            )
            
        except Exception as e:
            logger.error(f"Error handling anomaly: {e}")
    
    async def _send_anomaly_alert(self, anomaly: AnomalyDetection):
        """Send anomaly alert via WebSocket."""
        try:
            alert_data = {
                "id": str(anomaly.id),
                "rule_id": str(anomaly.rule_id),
                "rule_name": anomaly.rule_name,
                "detected_at": anomaly.detected_at.isoformat(),
                "measurement_type": anomaly.measurement_type,
                "actual_value": anomaly.actual_value,
                "threshold_value": anomaly.threshold_value,
                "threshold_type": anomaly.threshold_type,
                "severity": anomaly.severity,
                "farm_id": anomaly.farm_id,
                "device_id": anomaly.device_id,
                "location": anomaly.location
            }
            
            message = WebSocketMessage(
                message_type=MessageType.ALERT,
                data=alert_data,
                farm_id=anomaly.farm_id,
                device_id=anomaly.device_id
            )
            
            # Broadcast to relevant clients
            if anomaly.farm_id:
                await websocket_manager.broadcast_to_farm(anomaly.farm_id, message)
            else:
                await websocket_manager.broadcast_to_all(message)
                
        except Exception as e:
            logger.error(f"Failed to send anomaly alert: {e}")
    
    async def _execute_control_commands(self, anomaly: AnomalyDetection, commands: List[Dict[str, Any]]):
        """Execute automatic control commands."""
        # TODO: Implement control system integration
        logger.info(f"Would execute control commands for anomaly {anomaly.id}: {commands}")
    
    async def _continuous_evaluation(self):
        """Continuously evaluate sensor data for anomalies."""
        while self.is_running:
            try:
                # TODO: Implement continuous evaluation logic
                # This would typically:
                # 1. Query recent sensor readings
                # 2. Evaluate against active rules
                # 3. Handle any detected anomalies
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in continuous evaluation: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    def get_active_anomalies(self) -> List[AnomalyDetection]:
        """Get all active anomalies."""
        return list(self.active_anomalies.values())
    
    def get_anomaly(self, anomaly_id: UUID) -> Optional[AnomalyDetection]:
        """Get specific anomaly by ID."""
        return self.active_anomalies.get(anomaly_id)
    
    async def acknowledge_anomaly(self, anomaly_id: UUID, user: str) -> bool:
        """Acknowledge an anomaly."""
        if anomaly_id in self.active_anomalies:
            anomaly = self.active_anomalies[anomaly_id]
            anomaly.status = AnomalyStatus.ACKNOWLEDGED
            anomaly.acknowledged_by = user
            anomaly.acknowledged_at = datetime.utcnow()
            return True
        return False
    
    async def resolve_anomaly(
        self, 
        anomaly_id: UUID, 
        user: str, 
        notes: Optional[str] = None
    ) -> bool:
        """Resolve an anomaly."""
        if anomaly_id in self.active_anomalies:
            anomaly = self.active_anomalies[anomaly_id]
            anomaly.status = AnomalyStatus.RESOLVED
            anomaly.resolved_by = user
            anomaly.resolved_at = datetime.utcnow()
            anomaly.resolution_notes = notes
            
            # Remove from active anomalies
            del self.active_anomalies[anomaly_id]
            
            # TODO: Store in historical database
            
            return True
        return False


# Global anomaly detector instance
anomaly_detector = AnomalyDetector()