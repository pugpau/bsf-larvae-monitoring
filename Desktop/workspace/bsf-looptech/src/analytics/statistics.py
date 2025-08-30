"""
Statistical analysis service for sensor data.
Provides statistical calculations, trend analysis, and data aggregation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

from src.database.influxdb import InfluxDBClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AggregationMethod(str, Enum):
    """Statistical aggregation methods."""
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    STDDEV = "stddev"
    VARIANCE = "variance"
    PERCENTILE_25 = "p25"
    PERCENTILE_75 = "p75"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


class TimeGranularity(str, Enum):
    """Time granularity for aggregation."""
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    HOUR = "1h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1mo"


@dataclass
class StatisticalSummary:
    """Statistical summary of sensor data."""
    measurement_type: str
    device_id: Optional[str]
    farm_id: Optional[str]
    location: Optional[str]
    
    # Time range
    start_time: datetime
    end_time: datetime
    data_points: int
    
    # Basic statistics
    mean: float
    median: float
    min_value: float
    max_value: float
    std_dev: float
    variance: float
    
    # Percentiles
    p25: float
    p75: float
    p95: float
    p99: float
    
    # Quality metrics
    missing_data_percentage: float
    outlier_count: int
    
    # Trend indicators
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    
    # Additional metadata
    unit: Optional[str] = None
    quality_score: Optional[float] = None


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""
    timestamp: datetime
    value: float
    aggregation_method: Optional[str] = None
    data_count: Optional[int] = None


@dataclass
class TimeSeriesData:
    """Time series dataset."""
    measurement_type: str
    device_id: Optional[str]
    farm_id: Optional[str]
    location: Optional[str]
    
    start_time: datetime
    end_time: datetime
    granularity: TimeGranularity
    
    points: List[TimeSeriesPoint]
    total_points: int
    
    unit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StatisticalAnalyzer:
    """Statistical analysis service for sensor data."""
    
    def __init__(self):
        self.influx_client = InfluxDBClient()
        self.influx_client.connect()
    
    async def get_statistical_summary(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        location: Optional[str] = None,
        substrate_batch_id: Optional[str] = None
    ) -> Optional[StatisticalSummary]:
        """Get comprehensive statistical summary for sensor data."""
        try:
            # Build query filters
            filters = [
                f'r["_measurement"] == "sensor_data"',
                f'r["measurement_type"] == "{measurement_type}"',
                f'r["_field"] == "value"'
            ]
            
            if farm_id:
                filters.append(f'r["farm_id"] == "{farm_id}"')
            if device_id:
                filters.append(f'r["device_id"] == "{device_id}"')
            if location:
                filters.append(f'r["location"] == "{location}"')
            if substrate_batch_id:
                filters.append(f'r["substrate_batch_id"] == "{substrate_batch_id}"')
            
            filter_string = " and ".join(filters)
            
            # Query for basic statistics
            query = f'''
            from(bucket:"{self.influx_client.bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => {filter_string})
                |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
                |> yield(name: "raw_data")
            '''
            
            result = self.influx_client.query(query)
            values = []
            timestamps = []
            
            for table in result:
                for record in table.records:
                    values.append(record.get_value())
                    timestamps.append(record.get_time())
            
            if not values:
                return None
            
            # Calculate statistics
            import numpy as np
            
            np_values = np.array(values)
            
            # Basic statistics
            mean_val = np.mean(np_values)
            median_val = np.median(np_values)
            min_val = np.min(np_values)
            max_val = np.max(np_values)
            std_val = np.std(np_values)
            var_val = np.var(np_values)
            
            # Percentiles
            p25 = np.percentile(np_values, 25)
            p75 = np.percentile(np_values, 75)
            p95 = np.percentile(np_values, 95)
            p99 = np.percentile(np_values, 99)
            
            # Outlier detection (using IQR method)
            iqr = p75 - p25
            lower_bound = p25 - 1.5 * iqr
            upper_bound = p75 + 1.5 * iqr
            outliers = np_values[(np_values < lower_bound) | (np_values > upper_bound)]
            outlier_count = len(outliers)
            
            # Trend analysis
            trend_direction, trend_strength = self._calculate_trend(timestamps, values)
            
            # Quality metrics
            expected_points = (end_time - start_time).total_seconds() / 300  # 5-minute intervals
            missing_data_percentage = max(0, (expected_points - len(values)) / expected_points * 100)
            quality_score = max(0, 100 - missing_data_percentage - (outlier_count / len(values) * 100))
            
            return StatisticalSummary(
                measurement_type=measurement_type,
                device_id=device_id,
                farm_id=farm_id,
                location=location,
                start_time=start_time,
                end_time=end_time,
                data_points=len(values),
                mean=float(mean_val),
                median=float(median_val),
                min_value=float(min_val),
                max_value=float(max_val),
                std_dev=float(std_val),
                variance=float(var_val),
                p25=float(p25),
                p75=float(p75),
                p95=float(p95),
                p99=float(p99),
                missing_data_percentage=missing_data_percentage,
                outlier_count=outlier_count,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating statistical summary: {e}")
            return None
    
    async def get_time_series_data(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity,
        aggregation_method: AggregationMethod = AggregationMethod.MEAN,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        location: Optional[str] = None
    ) -> Optional[TimeSeriesData]:
        """Get time series data with specified granularity and aggregation."""
        try:
            # Build query filters
            filters = [
                f'r["_measurement"] == "sensor_data"',
                f'r["measurement_type"] == "{measurement_type}"',
                f'r["_field"] == "value"'
            ]
            
            if farm_id:
                filters.append(f'r["farm_id"] == "{farm_id}"')
            if device_id:
                filters.append(f'r["device_id"] == "{device_id}"')
            if location:
                filters.append(f'r["location"] == "{location}"')
            
            filter_string = " and ".join(filters)
            
            # Map aggregation method to InfluxDB function
            agg_function = self._map_aggregation_method(aggregation_method)
            
            query = f'''
            from(bucket:"{self.influx_client.bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => {filter_string})
                |> aggregateWindow(every: {granularity.value}, fn: {agg_function}, createEmpty: false)
                |> yield(name: "aggregated_data")
            '''
            
            result = self.influx_client.query(query)
            points = []
            
            for table in result:
                for record in table.records:
                    points.append(TimeSeriesPoint(
                        timestamp=record.get_time(),
                        value=record.get_value(),
                        aggregation_method=aggregation_method.value
                    ))
            
            # Sort by timestamp
            points.sort(key=lambda p: p.timestamp)
            
            return TimeSeriesData(
                measurement_type=measurement_type,
                device_id=device_id,
                farm_id=farm_id,
                location=location,
                start_time=start_time,
                end_time=end_time,
                granularity=granularity,
                points=points,
                total_points=len(points)
            )
            
        except Exception as e:
            logger.error(f"Error getting time series data: {e}")
            return None
    
    async def compare_periods(
        self,
        measurement_type: str,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Compare statistics between two time periods."""
        try:
            # Get summaries for both periods
            summary1 = await self.get_statistical_summary(
                measurement_type, period1_start, period1_end, farm_id, device_id
            )
            summary2 = await self.get_statistical_summary(
                measurement_type, period2_start, period2_end, farm_id, device_id
            )
            
            if not summary1 or not summary2:
                return None
            
            # Calculate differences
            comparison = {
                "period1": {
                    "start": period1_start.isoformat(),
                    "end": period1_end.isoformat(),
                    "summary": summary1.__dict__
                },
                "period2": {
                    "start": period2_start.isoformat(),
                    "end": period2_end.isoformat(),
                    "summary": summary2.__dict__
                },
                "differences": {
                    "mean_change": summary2.mean - summary1.mean,
                    "mean_change_percentage": ((summary2.mean - summary1.mean) / summary1.mean * 100) if summary1.mean != 0 else 0,
                    "std_dev_change": summary2.std_dev - summary1.std_dev,
                    "data_quality_change": (summary2.quality_score or 0) - (summary1.quality_score or 0),
                    "trend_change": {
                        "from": summary1.trend_direction,
                        "to": summary2.trend_direction,
                        "strength_change": summary2.trend_strength - summary1.trend_strength
                    }
                }
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing periods: {e}")
            return None
    
    async def detect_correlation(
        self,
        measurement_types: List[str],
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Detect correlations between different measurement types."""
        try:
            if len(measurement_types) < 2:
                raise ValueError("At least 2 measurement types required for correlation analysis")
            
            # Get time series data for each measurement type
            datasets = {}
            for measurement_type in measurement_types:
                data = await self.get_time_series_data(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    granularity=TimeGranularity.FIFTEEN_MINUTES,
                    farm_id=farm_id,
                    device_id=device_id
                )
                if data:
                    datasets[measurement_type] = data
            
            if len(datasets) < 2:
                return None
            
            # Align timestamps and calculate correlations
            import numpy as np
            from scipy.stats import pearsonr, spearmanr
            
            correlations = {}
            
            for i, type1 in enumerate(datasets.keys()):
                for type2 in list(datasets.keys())[i+1:]:
                    # Align data by timestamps
                    aligned_data1, aligned_data2 = self._align_time_series(
                        datasets[type1], datasets[type2]
                    )
                    
                    if len(aligned_data1) > 1:
                        # Calculate correlations
                        pearson_r, pearson_p = pearsonr(aligned_data1, aligned_data2)
                        spearman_r, spearman_p = spearmanr(aligned_data1, aligned_data2)
                        
                        correlations[f"{type1}_vs_{type2}"] = {
                            "pearson_correlation": float(pearson_r),
                            "pearson_p_value": float(pearson_p),
                            "spearman_correlation": float(spearman_r),
                            "spearman_p_value": float(spearman_p),
                            "data_points": len(aligned_data1),
                            "strength": self._interpret_correlation(abs(pearson_r))
                        }
            
            return {
                "measurement_types": measurement_types,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "correlations": correlations
            }
            
        except Exception as e:
            logger.error(f"Error detecting correlations: {e}")
            return None
    
    def _calculate_trend(self, timestamps: List[datetime], values: List[float]) -> Tuple[str, float]:
        """Calculate trend direction and strength."""
        try:
            import numpy as np
            from scipy.stats import linregress
            
            if len(values) < 2:
                return "stable", 0.0
            
            # Convert timestamps to numerical values
            time_nums = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
            
            # Linear regression
            slope, intercept, r_value, p_value, std_err = linregress(time_nums, values)
            
            # Determine trend direction
            if abs(slope) < std_err:  # Not statistically significant
                direction = "stable"
            elif slope > 0:
                direction = "increasing"
            else:
                direction = "decreasing"
            
            # Trend strength is based on R-squared value
            strength = abs(r_value) if p_value < 0.05 else 0.0
            
            return direction, float(strength)
            
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return "stable", 0.0
    
    def _map_aggregation_method(self, method: AggregationMethod) -> str:
        """Map aggregation method to InfluxDB function."""
        mapping = {
            AggregationMethod.MEAN: "mean",
            AggregationMethod.MEDIAN: "median",
            AggregationMethod.MIN: "min",
            AggregationMethod.MAX: "max",
            AggregationMethod.SUM: "sum",
            AggregationMethod.COUNT: "count",
            AggregationMethod.STDDEV: "stddev"
        }
        return mapping.get(method, "mean")
    
    def _align_time_series(self, data1: TimeSeriesData, data2: TimeSeriesData) -> Tuple[List[float], List[float]]:
        """Align two time series by timestamps."""
        # Create dictionaries for quick lookup
        dict1 = {point.timestamp: point.value for point in data1.points}
        dict2 = {point.timestamp: point.value for point in data2.points}
        
        # Find common timestamps
        common_timestamps = set(dict1.keys()) & set(dict2.keys())
        
        # Extract aligned values
        aligned1 = [dict1[ts] for ts in sorted(common_timestamps)]
        aligned2 = [dict2[ts] for ts in sorted(common_timestamps)]
        
        return aligned1, aligned2
    
    def _interpret_correlation(self, r_value: float) -> str:
        """Interpret correlation strength."""
        if r_value >= 0.8:
            return "very_strong"
        elif r_value >= 0.6:
            return "strong"
        elif r_value >= 0.4:
            return "moderate"
        elif r_value >= 0.2:
            return "weak"
        else:
            return "very_weak"


# Global statistical analyzer instance
statistical_analyzer = StatisticalAnalyzer()