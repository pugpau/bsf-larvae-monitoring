"""
時系列データ集約サービス
センサーデータの時間集約、移動平均、データ品質評価を提供
"""

import logging
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, timedelta, timezone
from enum import Enum
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.influxdb import get_influxdb_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AggregationWindow(str, Enum):
    """データ集約の時間窓"""
    MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    HOUR = "1h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1M"


class AggregationFunction(str, Enum):
    """集約関数"""
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    COUNT = "count"
    STDDEV = "stddev"
    FIRST = "first"
    LAST = "last"


class MovingAverageType(str, Enum):
    """移動平均の種類"""
    SIMPLE = "simple"          # 単純移動平均
    EXPONENTIAL = "exponential"  # 指数移動平均
    WEIGHTED = "weighted"      # 加重移動平均


class DataQuality(BaseModel):
    """データ品質評価結果"""
    completeness: float = Field(..., description="データ完全性 (0-1)")
    consistency: float = Field(..., description="データ一貫性 (0-1)")
    accuracy: float = Field(..., description="データ精度 (0-1)")
    timeliness: float = Field(..., description="データ適時性 (0-1)")
    overall_score: float = Field(..., description="総合品質スコア (0-1)")
    
    # 詳細メトリクス
    missing_data_rate: float = Field(..., description="欠損データ率")
    outlier_rate: float = Field(..., description="外れ値率")
    duplicate_rate: float = Field(..., description="重複データ率")
    data_freshness_hours: float = Field(..., description="データ鮮度（時間）")
    
    # 統計情報
    total_points: int = Field(..., description="総データポイント数")
    valid_points: int = Field(..., description="有効データポイント数")
    missing_points: int = Field(..., description="欠損データポイント数")
    outlier_points: int = Field(..., description="外れ値データポイント数")


class AggregatedData(BaseModel):
    """集約されたデータ"""
    timestamp: datetime
    value: float
    count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    std_dev: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MovingAverageData(BaseModel):
    """移動平均データ"""
    timestamp: datetime
    value: float
    period: int
    ma_type: MovingAverageType
    
    # 追加統計
    upper_bound: Optional[float] = None  # ボリンジャーバンド上限
    lower_bound: Optional[float] = None  # ボリンジャーバンド下限
    momentum: Optional[float] = None     # モメンタム


class TrendAnalysisResult(BaseModel):
    """トレンド分析結果"""
    trend_direction: str = Field(..., description="トレンド方向: up/down/stable")
    trend_strength: float = Field(..., description="トレンド強度 (0-1)")
    slope: float = Field(..., description="傾き")
    r_squared: float = Field(..., description="決定係数")
    
    # 予測値
    next_period_forecast: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    
    # 季節性
    seasonality_detected: bool = Field(default=False)
    seasonal_period: Optional[int] = None
    seasonal_strength: Optional[float] = None


class DataAggregationService:
    """データ集約サービス"""
    
    def __init__(self):
        self.influx_client = get_influxdb_client()
    
    async def aggregate_sensor_data(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        window: AggregationWindow,
        aggregation_func: AggregationFunction = AggregationFunction.MEAN,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[AggregatedData]:
        """
        センサーデータを指定された時間窓で集約
        """
        try:
            query_client = self.influx_client.query_api()
            
            # Flux クエリを構築
            flux_query = f'''
            from(bucket: "bsf_monitoring")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "{measurement_type}")
            '''
            
            # フィルター条件を追加
            if farm_id:
                flux_query += f'|> filter(fn: (r) => r["farm_id"] == "{farm_id}")\n'
            if device_id:
                flux_query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'
            if location:
                flux_query += f'|> filter(fn: (r) => r["location"] == "{location}")\n'
            
            # 集約を追加
            flux_query += f'''
            |> aggregateWindow(every: {window.value}, fn: {aggregation_func.value}, createEmpty: false)
            |> yield(name: "aggregated")
            '''
            
            logger.debug(f"Executing aggregation query: {flux_query}")
            
            # クエリ実行
            tables = query_client.query(query=flux_query)
            
            aggregated_data = []
            for table in tables:
                for record in table.records:
                    # 統計情報を計算（追加クエリが必要な場合）
                    timestamp = record.get_time()
                    value = record.get_value()
                    
                    if value is not None:
                        aggregated_data.append(AggregatedData(
                            timestamp=timestamp,
                            value=float(value),
                            count=1  # 実際の集約では正しいカウントを取得
                        ))
            
            logger.info(f"Aggregated {len(aggregated_data)} data points for {measurement_type}")
            return aggregated_data
            
        except Exception as e:
            logger.error(f"Error aggregating sensor data: {e}")
            raise
    
    async def calculate_moving_average(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        period: int,
        ma_type: MovingAverageType = MovingAverageType.SIMPLE,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> List[MovingAverageData]:
        """
        移動平均を計算
        """
        try:
            # 元データを取得
            query_client = self.influx_client.query_api()
            
            flux_query = f'''
            from(bucket: "bsf_monitoring")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "{measurement_type}")
            '''
            
            if farm_id:
                flux_query += f'|> filter(fn: (r) => r["farm_id"] == "{farm_id}")\n'
            if device_id:
                flux_query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'
            
            flux_query += '|> sort(columns: ["_time"])\n'
            
            tables = query_client.query(query=flux_query)
            
            # データをPandasで処理
            data_points = []
            for table in tables:
                for record in table.records:
                    if record.get_value() is not None:
                        data_points.append({
                            'timestamp': record.get_time(),
                            'value': float(record.get_value())
                        })
            
            if not data_points:
                return []
            
            df = pd.DataFrame(data_points)
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # 移動平均を計算
            if ma_type == MovingAverageType.SIMPLE:
                df['ma'] = df['value'].rolling(window=period).mean()
            elif ma_type == MovingAverageType.EXPONENTIAL:
                df['ma'] = df['value'].ewm(span=period).mean()
            elif ma_type == MovingAverageType.WEIGHTED:
                weights = np.arange(1, period + 1)
                df['ma'] = df['value'].rolling(window=period).apply(
                    lambda x: np.average(x, weights=weights), raw=True
                )
            
            # ボリンジャーバンドを計算
            rolling_std = df['value'].rolling(window=period).std()
            df['upper_band'] = df['ma'] + (rolling_std * 2)
            df['lower_band'] = df['ma'] - (rolling_std * 2)
            
            # モメンタムを計算
            df['momentum'] = df['value'] - df['value'].shift(period)
            
            # 結果を変換
            ma_data = []
            for idx, row in df.iterrows():
                if not pd.isna(row['ma']):
                    ma_data.append(MovingAverageData(
                        timestamp=idx,
                        value=row['ma'],
                        period=period,
                        ma_type=ma_type,
                        upper_bound=row['upper_band'] if not pd.isna(row['upper_band']) else None,
                        lower_bound=row['lower_band'] if not pd.isna(row['lower_band']) else None,
                        momentum=row['momentum'] if not pd.isna(row['momentum']) else None
                    ))
            
            logger.info(f"Calculated {len(ma_data)} moving average points")
            return ma_data
            
        except Exception as e:
            logger.error(f"Error calculating moving average: {e}")
            raise
    
    async def evaluate_data_quality(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        expected_interval_minutes: int = 1,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> DataQuality:
        """
        データ品質を評価
        """
        try:
            query_client = self.influx_client.query_api()
            
            # 全データを取得
            flux_query = f'''
            from(bucket: "bsf_monitoring")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "{measurement_type}")
            '''
            
            if farm_id:
                flux_query += f'|> filter(fn: (r) => r["farm_id"] == "{farm_id}")\n'
            if device_id:
                flux_query += f'|> filter(fn: (r) => r["device_id"] == "{device_id}")\n'
            
            tables = query_client.query(query=flux_query)
            
            # データを収集
            values = []
            timestamps = []
            for table in tables:
                for record in table.records:
                    if record.get_value() is not None:
                        values.append(float(record.get_value()))
                        timestamps.append(record.get_time())
            
            if not values:
                return DataQuality(
                    completeness=0.0,
                    consistency=0.0,
                    accuracy=0.0,
                    timeliness=0.0,
                    overall_score=0.0,
                    missing_data_rate=1.0,
                    outlier_rate=0.0,
                    duplicate_rate=0.0,
                    data_freshness_hours=999.0,
                    total_points=0,
                    valid_points=0,
                    missing_points=0,
                    outlier_points=0
                )
            
            # 統計計算
            values_array = np.array(values)
            timestamps_array = pd.to_datetime(timestamps)
            
            # 期待されるデータポイント数
            total_duration = end_time - start_time
            expected_points = int(total_duration.total_seconds() / (expected_interval_minutes * 60))
            actual_points = len(values)
            
            # 完全性 (Completeness)
            completeness = min(actual_points / expected_points, 1.0) if expected_points > 0 else 0.0
            missing_points = max(expected_points - actual_points, 0)
            missing_data_rate = missing_points / expected_points if expected_points > 0 else 0.0
            
            # 一貫性 (Consistency) - 重複データ率
            unique_timestamps = len(set(timestamps))
            duplicate_rate = 1.0 - (unique_timestamps / len(timestamps)) if timestamps else 0.0
            consistency = 1.0 - duplicate_rate
            
            # 精度 (Accuracy) - 外れ値率
            if len(values) > 1:
                q75, q25 = np.percentile(values_array, [75, 25])
                iqr = q75 - q25
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                outliers = values_array[(values_array < lower_bound) | (values_array > upper_bound)]
                outlier_rate = len(outliers) / len(values)
                accuracy = 1.0 - outlier_rate
                outlier_points = len(outliers)
            else:
                outlier_rate = 0.0
                accuracy = 1.0
                outlier_points = 0
            
            # 適時性 (Timeliness) - データ鮮度
            if timestamps:
                latest_time = max(timestamps_array)
                current_time = datetime.now(timezone.utc)
                freshness_hours = (current_time - latest_time).total_seconds() / 3600
                timeliness = max(0.0, 1.0 - (freshness_hours / 24))  # 24時間で0になる
            else:
                freshness_hours = 999.0
                timeliness = 0.0
            
            # 総合スコア
            overall_score = (completeness + consistency + accuracy + timeliness) / 4
            
            return DataQuality(
                completeness=completeness,
                consistency=consistency,
                accuracy=accuracy,
                timeliness=timeliness,
                overall_score=overall_score,
                missing_data_rate=missing_data_rate,
                outlier_rate=outlier_rate,
                duplicate_rate=duplicate_rate,
                data_freshness_hours=freshness_hours,
                total_points=expected_points,
                valid_points=actual_points,
                missing_points=missing_points,
                outlier_points=outlier_points
            )
            
        except Exception as e:
            logger.error(f"Error evaluating data quality: {e}")
            raise
    
    async def get_aggregation_summary(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        farm_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        集約データのサマリーを取得
        """
        try:
            # 複数の時間窓で集約
            summaries = {}
            
            windows = [
                AggregationWindow.HOUR,
                AggregationWindow.DAY,
                AggregationWindow.WEEK
            ]
            
            for window in windows:
                aggregated_data = await self.aggregate_sensor_data(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    window=window,
                    farm_id=farm_id
                )
                
                if aggregated_data:
                    values = [data.value for data in aggregated_data]
                    summaries[window.value] = {
                        "count": len(values),
                        "mean": np.mean(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "std": np.std(values),
                        "latest": values[-1] if values else None
                    }
            
            # データ品質評価
            quality = await self.evaluate_data_quality(
                measurement_type=measurement_type,
                start_time=start_time,
                end_time=end_time,
                farm_id=farm_id
            )
            
            return {
                "measurement_type": measurement_type,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "farm_id": farm_id,
                "aggregations": summaries,
                "data_quality": quality.model_dump(),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating aggregation summary: {e}")
            raise


# グローバルインスタンス
data_aggregation_service = DataAggregationService()