"""
API routes for analytics and anomaly detection.
Provides endpoints for managing rules and viewing anomalies.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models import (
    AnomalyDetectionRule, AnomalyDetection,
    RuleCreateRequest, RuleUpdateRequest,
    RuleStatus, RuleSeverity, AnomalyStatus, ThresholdType
)
from src.analytics.repository import AnomalyRuleRepository, AnomalyDetectionRepository
from src.analytics.anomaly_detector import anomaly_detector
from src.analytics.statistics import (
    statistical_analyzer,
    AggregationMethod, TimeGranularity
)
from src.utils.logging import get_logger

logger = get_logger(__name__)
from src.database.postgresql import get_async_session
from src.auth.security import require_permission
from src.auth.models import User, Permission

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Dependency to get rule repository
async def get_rule_repository(session: AsyncSession = Depends(get_async_session)) -> AnomalyRuleRepository:
    return AnomalyRuleRepository(session)


# Dependency to get anomaly repository
async def get_anomaly_repository(session: AsyncSession = Depends(get_async_session)) -> AnomalyDetectionRepository:
    return AnomalyDetectionRepository(session)


# Anomaly Detection Rules

@router.post("/rules", response_model=AnomalyDetectionRule, status_code=201)
async def create_rule(
    rule_request: RuleCreateRequest,
    rule_repo: AnomalyRuleRepository = Depends(get_rule_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Create a new anomaly detection rule."""
    try:
        # Create rule model
        rule = AnomalyDetectionRule(
            **rule_request.model_dump(),
            created_by=str(current_user.username)
        )
        
        # Save to database
        created_rule = await rule_repo.create_rule(rule)
        if not created_rule:
            raise HTTPException(status_code=500, detail="Failed to create rule")
        
        # Add to anomaly detector
        await anomaly_detector.add_rule(created_rule)
        
        return created_rule
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating rule: {str(e)}")


@router.get("/rules", response_model=List[AnomalyDetectionRule])
async def get_rules(
    status: Optional[RuleStatus] = Query(None),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    rule_repo: AnomalyRuleRepository = Depends(get_rule_repository),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get all anomaly detection rules with optional filters."""
    return await rule_repo.get_all_rules(
        status=status,
        farm_id=farm_id,
        device_id=device_id,
        severity=severity
    )


@router.get("/rules/{rule_id}", response_model=AnomalyDetectionRule)
async def get_rule(
    rule_id: UUID,
    rule_repo: AnomalyRuleRepository = Depends(get_rule_repository),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get a specific anomaly detection rule."""
    rule = await rule_repo.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=AnomalyDetectionRule)
async def update_rule(
    rule_id: UUID,
    rule_update: RuleUpdateRequest,
    rule_repo: AnomalyRuleRepository = Depends(get_rule_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Update an anomaly detection rule."""
    # Get current rule
    existing_rule = await rule_repo.get_rule(rule_id)
    if not existing_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update rule
    updates = rule_update.model_dump(exclude_unset=True)
    updated_rule = await rule_repo.update_rule(rule_id, updates)
    
    if not updated_rule:
        raise HTTPException(status_code=500, detail="Failed to update rule")
    
    # Update in anomaly detector
    await anomaly_detector.update_rule(rule_id, updated_rule)
    
    return updated_rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: UUID,
    rule_repo: AnomalyRuleRepository = Depends(get_rule_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Delete an anomaly detection rule."""
    success = await rule_repo.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Remove from anomaly detector
    await anomaly_detector.delete_rule(rule_id)
    
    return {"message": "Rule deleted successfully"}


# Anomaly Detections

@router.get("/anomalies", response_model=List[AnomalyDetection])
async def get_anomalies(
    status: Optional[AnomalyStatus] = Query(None),
    severity: Optional[RuleSeverity] = Query(None),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    rule_id: Optional[UUID] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get anomaly detections with filters."""
    return await anomaly_repo.get_anomalies(
        status=status,
        severity=severity,
        farm_id=farm_id,
        device_id=device_id,
        rule_id=rule_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )


@router.get("/anomalies/{anomaly_id}", response_model=AnomalyDetection)
async def get_anomaly(
    anomaly_id: UUID,
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get a specific anomaly detection."""
    anomaly = await anomaly_repo.get_anomaly(anomaly_id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return anomaly


@router.post("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: UUID,
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Acknowledge an anomaly detection."""
    updated_anomaly = await anomaly_repo.update_anomaly_status(
        anomaly_id=anomaly_id,
        status=AnomalyStatus.ACKNOWLEDGED,
        user=str(current_user.username)
    )
    
    if not updated_anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    # Update in anomaly detector
    await anomaly_detector.acknowledge_anomaly(anomaly_id, str(current_user.username))
    
    return {"message": "Anomaly acknowledged", "anomaly": updated_anomaly}


@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: UUID,
    resolution_notes: Optional[str] = None,
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Resolve an anomaly detection."""
    updated_anomaly = await anomaly_repo.update_anomaly_status(
        anomaly_id=anomaly_id,
        status=AnomalyStatus.RESOLVED,
        user=str(current_user.username),
        notes=resolution_notes
    )
    
    if not updated_anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    # Update in anomaly detector
    await anomaly_detector.resolve_anomaly(anomaly_id, str(current_user.username), resolution_notes)
    
    return {"message": "Anomaly resolved", "anomaly": updated_anomaly}


@router.post("/anomalies/{anomaly_id}/false-positive")
async def mark_false_positive(
    anomaly_id: UUID,
    notes: Optional[str] = None,
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Mark an anomaly as false positive."""
    updated_anomaly = await anomaly_repo.update_anomaly_status(
        anomaly_id=anomaly_id,
        status=AnomalyStatus.FALSE_POSITIVE,
        user=str(current_user.username),
        notes=notes
    )
    
    if not updated_anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    return {"message": "Anomaly marked as false positive", "anomaly": updated_anomaly}


# Statistics and Analytics

@router.get("/statistics", response_model=Dict[str, Any])
async def get_anomaly_statistics(
    farm_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    anomaly_repo: AnomalyDetectionRepository = Depends(get_anomaly_repository),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get anomaly detection statistics."""
    end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = end_time - timedelta(days=days)
    
    stats = await anomaly_repo.get_anomaly_statistics(
        farm_id=farm_id,
        start_time=start_time,
        end_time=end_time
    )
    
    # Add additional statistics
    stats["period_days"] = days
    stats["generated_at"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    
    return stats


@router.get("/active-anomalies", response_model=List[AnomalyDetection])
async def get_active_anomalies(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get currently active anomalies from the detector."""
    return anomaly_detector.get_active_anomalies()


# Detector Management

@router.get("/detector/status")
async def get_detector_status(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get anomaly detector status."""
    return {
        "is_running": anomaly_detector.is_running,
        "loaded_rules": len(anomaly_detector.rules),
        "active_anomalies": len(anomaly_detector.active_anomalies),
        "cooldown_entries": len(anomaly_detector.rule_cooldowns)
    }


@router.post("/detector/start")
async def start_detector(
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Start the anomaly detection engine."""
    await anomaly_detector.start()
    return {"message": "Anomaly detector started"}


@router.post("/detector/stop")
async def stop_detector(
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Stop the anomaly detection engine."""
    await anomaly_detector.stop()
    return {"message": "Anomaly detector stopped"}


@router.post("/detector/reload-rules")
async def reload_rules(
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Reload anomaly detection rules."""
    await anomaly_detector.load_rules()
    return {"message": "Rules reloaded successfully"}


# Configuration Helpers

@router.get("/threshold-types")
async def get_threshold_types(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available threshold types."""
    return [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in ThresholdType]


@router.get("/severities")
async def get_severities(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available severity levels."""
    return [{"value": s.value, "label": s.value.title()} for s in RuleSeverity]


@router.get("/rule-statuses")
async def get_rule_statuses(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available rule statuses."""
    return [{"value": s.value, "label": s.value.title()} for s in RuleStatus]


# Statistical Analysis Endpoints

@router.get("/statistics/summary")
async def get_statistical_summary(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    substrate_batch_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get comprehensive statistical summary for sensor data."""
    summary = await statistical_analyzer.get_statistical_summary(
        measurement_type=measurement_type,
        start_time=start_time,
        end_time=end_time,
        farm_id=farm_id,
        device_id=device_id,
        location=location,
        substrate_batch_id=substrate_batch_id
    )
    
    if not summary:
        raise HTTPException(status_code=404, detail="No data found for the specified criteria")
    
    return summary


@router.get("/statistics/time-series")
async def get_time_series_data(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    granularity: TimeGranularity,
    aggregation_method: AggregationMethod = Query(AggregationMethod.MEAN),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get time series data with specified granularity and aggregation."""
    data = await statistical_analyzer.get_time_series_data(
        measurement_type=measurement_type,
        start_time=start_time,
        end_time=end_time,
        granularity=granularity,
        aggregation_method=aggregation_method,
        farm_id=farm_id,
        device_id=device_id,
        location=location
    )
    
    if not data:
        raise HTTPException(status_code=404, detail="No data found for the specified criteria")
    
    return data


@router.get("/statistics/compare-periods")
async def compare_periods(
    measurement_type: str,
    period1_start: datetime,
    period1_end: datetime,
    period2_start: datetime,
    period2_end: datetime,
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Compare statistics between two time periods."""
    comparison = await statistical_analyzer.compare_periods(
        measurement_type=measurement_type,
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end,
        farm_id=farm_id,
        device_id=device_id
    )
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Insufficient data for comparison")
    
    return comparison


@router.get("/statistics/correlation")
async def detect_correlation(
    measurement_types: List[str] = Query(..., min_items=2),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Detect correlations between different measurement types."""
    correlations = await statistical_analyzer.detect_correlation(
        measurement_types=measurement_types,
        start_time=start_time,
        end_time=end_time,
        farm_id=farm_id,
        device_id=device_id
    )
    
    if not correlations:
        raise HTTPException(status_code=404, detail="Insufficient data for correlation analysis")
    
    return correlations


@router.get("/statistics/dashboard")
async def get_analytics_dashboard(
    farm_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get comprehensive analytics dashboard data."""
    end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = end_time - timedelta(days=days)
    
    # Common measurement types for BSF monitoring
    measurement_types = ["temperature", "humidity", "pressure", "h2s", "nh3"]
    
    dashboard_data = {
        "time_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "days": days
        },
        "farm_id": farm_id,
        "summaries": {},
        "trends": {},
        "correlations": None,
        "quality_metrics": {}
    }
    
    # Get summaries for each measurement type
    for measurement_type in measurement_types:
        try:
            summary = await statistical_analyzer.get_statistical_summary(
                measurement_type=measurement_type,
                start_time=start_time,
                end_time=end_time,
                farm_id=farm_id
            )
            
            if summary:
                dashboard_data["summaries"][measurement_type] = {
                    "mean": summary.mean,
                    "min": summary.min_value,
                    "max": summary.max_value,
                    "std_dev": summary.std_dev,
                    "trend_direction": summary.trend_direction,
                    "trend_strength": summary.trend_strength,
                    "quality_score": summary.quality_score,
                    "data_points": summary.data_points
                }
                
                dashboard_data["quality_metrics"][measurement_type] = {
                    "quality_score": summary.quality_score,
                    "missing_data_percentage": summary.missing_data_percentage,
                    "outlier_count": summary.outlier_count
                }
        except Exception as e:
            logger.error(f"Error getting summary for {measurement_type}: {e}")
    
    # Get correlation analysis
    try:
        available_types = list(dashboard_data["summaries"].keys())
        if len(available_types) >= 2:
            correlations = await statistical_analyzer.detect_correlation(
                measurement_types=available_types[:5],  # Limit to avoid too many combinations
                start_time=start_time,
                end_time=end_time,
                farm_id=farm_id
            )
            dashboard_data["correlations"] = correlations
    except Exception as e:
        logger.error(f"Error getting correlations: {e}")
    
    return dashboard_data


# Data Aggregation Endpoints

@router.get("/aggregation/data")
async def aggregate_sensor_data(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    window: str = Query(..., description="Aggregation window (1m, 5m, 15m, 30m, 1h, 6h, 12h, 1d, 1w, 1M)"),
    aggregation_func: str = Query("mean", description="Aggregation function"),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get aggregated sensor data."""
    from src.analytics.aggregation import data_aggregation_service, AggregationWindow, AggregationFunction
    
    try:
        # Enum値を検証
        window_enum = AggregationWindow(window)
        func_enum = AggregationFunction(aggregation_func)
        
        aggregated_data = await data_aggregation_service.aggregate_sensor_data(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            window=window_enum,
            aggregation_func=func_enum,
            farm_id=farm_id,
            device_id=device_id,
            location=location
        )
        
        return {
            "measurement_type": measurement_type,
            "aggregation_window": window,
            "aggregation_function": aggregation_func,
            "data_points": len(aggregated_data),
            "data": [
                {
                    "timestamp": data.timestamp.isoformat(),
                    "value": data.value,
                    "count": data.count,
                    "min_value": data.min_value,
                    "max_value": data.max_value,
                    "std_dev": data.std_dev
                }
                for data in aggregated_data
            ]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@router.get("/aggregation/moving-average")
async def calculate_moving_average(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    period: int = Query(..., ge=2, le=100, description="Moving average period"),
    ma_type: str = Query("simple", description="Moving average type: simple, exponential, weighted"),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Calculate moving average for sensor data."""
    from src.analytics.aggregation import data_aggregation_service, MovingAverageType
    
    try:
        ma_type_enum = MovingAverageType(ma_type)
        
        ma_data = await data_aggregation_service.calculate_moving_average(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            period=period,
            ma_type=ma_type_enum,
            farm_id=farm_id,
            device_id=device_id
        )
        
        return {
            "measurement_type": measurement_type,
            "period": period,
            "ma_type": ma_type,
            "data_points": len(ma_data),
            "data": [
                {
                    "timestamp": data.timestamp.isoformat(),
                    "value": data.value,
                    "upper_bound": data.upper_bound,
                    "lower_bound": data.lower_bound,
                    "momentum": data.momentum
                }
                for data in ma_data
            ]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Moving average calculation failed: {str(e)}")


@router.get("/aggregation/quality")
async def evaluate_data_quality(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    expected_interval_minutes: int = Query(1, ge=1, le=60),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Evaluate data quality for sensor measurements."""
    from src.analytics.aggregation import data_aggregation_service
    
    try:
        quality = await data_aggregation_service.evaluate_data_quality(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            expected_interval_minutes=expected_interval_minutes,
            farm_id=farm_id,
            device_id=device_id
        )
        
        return quality.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality evaluation failed: {str(e)}")


# Trend Analysis Endpoints

@router.get("/trend/analysis")
async def analyze_trend(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    trend_type: str = Query("linear", description="Trend type: linear, polynomial, seasonal"),
    aggregation_window: str = Query("1h", description="Data aggregation window"),
    farm_id: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Analyze trends in sensor data."""
    from src.analytics.trend_analysis import trend_analysis_engine, TrendType
    from src.analytics.aggregation import AggregationWindow
    
    try:
        trend_type_enum = TrendType(trend_type)
        window_enum = AggregationWindow(aggregation_window)
        
        trend_result = await trend_analysis_engine.analyze_trend(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            trend_type=trend_type_enum,
            aggregation_window=window_enum,
            farm_id=farm_id,
            device_id=device_id
        )
        
        return trend_result.model_dump()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend analysis failed: {str(e)}")


@router.get("/trend/change-points")
async def detect_change_points(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    sensitivity: float = Query(0.1, ge=0.01, le=1.0, description="Change detection sensitivity"),
    farm_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Detect change points in sensor data."""
    from src.analytics.trend_analysis import trend_analysis_engine
    
    try:
        change_points = await trend_analysis_engine.detect_change_points(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            sensitivity=sensitivity,
            farm_id=farm_id
        )
        
        return {
            "measurement_type": measurement_type,
            "sensitivity": sensitivity,
            "change_points_detected": len(change_points),
            "change_points": [
                {
                    "timestamp": cp.timestamp.isoformat(),
                    "change_magnitude": cp.change_magnitude,
                    "confidence": cp.confidence,
                    "change_type": cp.change_type
                }
                for cp in change_points
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Change point detection failed: {str(e)}")


@router.get("/trend/forecast")
async def forecast_values(
    measurement_type: str,
    start_time: datetime,
    end_time: datetime,
    forecast_periods: int = Query(24, ge=1, le=168, description="Number of periods to forecast"),
    model_type: str = Query("linear", description="Forecasting model type"),
    farm_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Forecast future sensor values."""
    from src.analytics.trend_analysis import trend_analysis_engine
    
    try:
        forecast_result = await trend_analysis_engine.forecast_values(
            measurement_type=measurement_type,
            start_time=start_time,
            end_time=end_time,
            forecast_periods=forecast_periods,
            model_type=model_type,
            farm_id=farm_id
        )
        
        return {
            "measurement_type": measurement_type,
            "model_type": forecast_result.model_type,
            "forecast_periods": forecast_periods,
            "accuracy_metrics": forecast_result.accuracy_metrics,
            "forecast": [
                {
                    "timestamp": ts.isoformat(),
                    "value": val,
                    "confidence_lower": ci[0],
                    "confidence_upper": ci[1]
                }
                for ts, val, ci in zip(
                    forecast_result.forecast_timestamps,
                    forecast_result.forecast_values,
                    forecast_result.confidence_intervals
                )
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


# Report Generation Endpoints

@router.post("/reports/generate")
async def generate_report(
    report_type: str,
    format: str,
    start_time: datetime,
    end_time: datetime,
    measurement_types: List[str] = Query(...),
    farm_id: Optional[str] = Query(None),
    include_quality: bool = Query(True),
    include_anomalies: bool = Query(True),
    include_trends: bool = Query(True),
    current_user: User = Depends(require_permission(Permission.MANAGE_ANALYTICS))
):
    """Generate a comprehensive analytics report."""
    from src.analytics.report_generator import report_generator, ReportConfig, ReportType, ReportFormat, ReportSchedule
    
    try:
        report_type_enum = ReportType(report_type)
        format_enum = ReportFormat(format)
        
        config = ReportConfig(
            report_type=report_type_enum,
            format=format_enum,
            schedule=ReportSchedule.ON_DEMAND,
            farm_id=farm_id,
            measurement_types=measurement_types,
            include_quality_metrics=include_quality,
            include_anomalies=include_anomalies,
            include_trends=include_trends
        )
        
        report = await report_generator.generate_report(
            config=config,
            start_time=start_time,
            end_time=end_time
        )
        
        response_data = {
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "format": report.format.value,
            "generated_at": report.generated_at.isoformat(),
            "summary": report.summary,
            "sections_count": len(report.sections)
        }
        
        if report.file_path:
            response_data["file_path"] = report.file_path
            response_data["file_size"] = report.file_size
        
        if format_enum == ReportFormat.JSON:
            # JSONの場合は完全なレポートデータを返す
            response_data["report_data"] = report.model_dump()
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# Configuration Helpers for Statistics

@router.get("/statistics/aggregation-methods")
async def get_aggregation_methods(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available aggregation methods."""
    return [
        {"value": method.value, "label": method.value.upper()}
        for method in AggregationMethod
    ]


@router.get("/statistics/time-granularities")
async def get_time_granularities(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available time granularities."""
    granularity_labels = {
        TimeGranularity.MINUTE: "1 Minute",
        TimeGranularity.FIVE_MINUTES: "5 Minutes",
        TimeGranularity.FIFTEEN_MINUTES: "15 Minutes",
        TimeGranularity.THIRTY_MINUTES: "30 Minutes",
        TimeGranularity.HOUR: "1 Hour",
        TimeGranularity.SIX_HOURS: "6 Hours",
        TimeGranularity.TWELVE_HOURS: "12 Hours",
        TimeGranularity.DAY: "1 Day",
        TimeGranularity.WEEK: "1 Week",
        TimeGranularity.MONTH: "1 Month"
    }
    
    return [
        {"value": granularity.value, "label": granularity_labels[granularity]}
        for granularity in TimeGranularity
    ]


@router.get("/config/aggregation-windows")
async def get_aggregation_windows(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available aggregation windows."""
    from src.analytics.aggregation import AggregationWindow
    
    return [
        {"value": window.value, "label": window.value}
        for window in AggregationWindow
    ]


@router.get("/config/trend-types")
async def get_trend_types(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available trend analysis types."""
    from src.analytics.trend_analysis import TrendType
    
    return [
        {"value": trend_type.value, "label": trend_type.value.title()}
        for trend_type in TrendType
    ]


@router.get("/config/report-types")
async def get_report_types(
    current_user: User = Depends(require_permission(Permission.VIEW_ANALYTICS))
):
    """Get available report types."""
    from src.analytics.report_generator import ReportType, ReportFormat
    
    return {
        "report_types": [
            {"value": rt.value, "label": rt.value.replace('_', ' ').title()}
            for rt in ReportType
        ],
        "formats": [
            {"value": rf.value, "label": rf.value.upper()}
            for rf in ReportFormat
        ]
    }