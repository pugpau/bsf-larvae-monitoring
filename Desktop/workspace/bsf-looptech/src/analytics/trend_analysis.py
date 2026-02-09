"""
トレンド分析エンジン
長期トレンド検出、季節性分析、予測機能を提供
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
from pydantic import BaseModel, Field

from src.database.influxdb import get_influxdb_client
from src.analytics.aggregation import (
    TrendAnalysisResult, DataAggregationService, 
    AggregationWindow, AggregationFunction
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TrendType(str, Enum):
    """トレンドの種類"""
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"


class SeasonalPattern(BaseModel):
    """季節性パターン"""
    period: int = Field(..., description="周期（データポイント数）")
    strength: float = Field(..., description="季節性の強度 (0-1)")
    amplitude: float = Field(..., description="振幅")
    phase_shift: float = Field(..., description="位相シフト")
    trend_component: List[float] = Field(..., description="トレンド成分")
    seasonal_component: List[float] = Field(..., description="季節成分")
    residual_component: List[float] = Field(..., description="残差成分")


class ForecastResult(BaseModel):
    """予測結果"""
    forecast_values: List[float] = Field(..., description="予測値")
    forecast_timestamps: List[datetime] = Field(..., description="予測時刻")
    confidence_intervals: List[Tuple[float, float]] = Field(..., description="信頼区間")
    model_type: str = Field(..., description="使用されたモデル")
    accuracy_metrics: Dict[str, float] = Field(..., description="精度メトリクス")


class ChangePoint(BaseModel):
    """変化点"""
    timestamp: datetime = Field(..., description="変化点の時刻")
    change_magnitude: float = Field(..., description="変化の大きさ")
    confidence: float = Field(..., description="変化点の信頼度")
    change_type: str = Field(..., description="変化の種類: increase/decrease/volatility")


class TrendAnalysisEngine:
    """トレンド分析エンジン"""
    
    def __init__(self):
        self.influx_client = get_influxdb_client()
        self.aggregation_service = DataAggregationService()
    
    async def analyze_trend(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        trend_type: TrendType = TrendType.LINEAR,
        aggregation_window: AggregationWindow = AggregationWindow.HOUR,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> TrendAnalysisResult:
        """
        トレンド分析を実行
        """
        try:
            # 集約データを取得
            aggregated_data = await self.aggregation_service.aggregate_sensor_data(
                measurement_type=measurement_type,
                start_time=start_time,
                end_time=end_time,
                window=aggregation_window,
                farm_id=farm_id,
                device_id=device_id
            )
            
            if len(aggregated_data) < 3:
                logger.warning(f"Insufficient data for trend analysis: {len(aggregated_data)} points")
                return TrendAnalysisResult(
                    trend_direction="unknown",
                    trend_strength=0.0,
                    slope=0.0,
                    r_squared=0.0
                )
            
            # データをPandasで処理
            df = pd.DataFrame([
                {"timestamp": data.timestamp, "value": data.value}
                for data in aggregated_data
            ])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # トレンド分析
            if trend_type == TrendType.LINEAR:
                return await self._analyze_linear_trend(df)
            elif trend_type == TrendType.POLYNOMIAL:
                return await self._analyze_polynomial_trend(df)
            elif trend_type == TrendType.SEASONAL:
                return await self._analyze_seasonal_trend(df)
            else:
                return await self._analyze_linear_trend(df)
                
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            raise
    
    async def _analyze_linear_trend(self, df: pd.DataFrame) -> TrendAnalysisResult:
        """線形トレンド分析"""
        try:
            # 時間を数値に変換
            df['time_numeric'] = (df.index - df.index[0]).total_seconds()
            
            X = df['time_numeric'].values.reshape(-1, 1)
            y = df['value'].values
            
            # 線形回帰
            model = LinearRegression()
            model.fit(X, y)
            
            y_pred = model.predict(X)
            r_squared = r2_score(y, y_pred)
            slope = model.coef_[0]
            
            # トレンド方向と強度を判定
            if abs(slope) < 1e-6:
                trend_direction = "stable"
                trend_strength = 0.0
            elif slope > 0:
                trend_direction = "up"
                trend_strength = min(abs(slope) * 100, 1.0)
            else:
                trend_direction = "down"
                trend_strength = min(abs(slope) * 100, 1.0)
            
            # 予測値を計算（次の期間）
            next_time = df['time_numeric'].iloc[-1] + (df['time_numeric'].iloc[-1] - df['time_numeric'].iloc[-2])
            next_forecast = model.predict([[next_time]])[0]
            
            # 信頼区間を計算
            residuals = y - y_pred
            mse = np.mean(residuals ** 2)
            std_error = np.sqrt(mse)
            confidence_margin = 1.96 * std_error  # 95%信頼区間
            
            return TrendAnalysisResult(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                slope=slope,
                r_squared=r_squared,
                next_period_forecast=next_forecast,
                confidence_interval_lower=next_forecast - confidence_margin,
                confidence_interval_upper=next_forecast + confidence_margin
            )
            
        except Exception as e:
            logger.error(f"Error in linear trend analysis: {e}")
            raise
    
    async def _analyze_polynomial_trend(self, df: pd.DataFrame, degree: int = 2) -> TrendAnalysisResult:
        """多項式トレンド分析"""
        try:
            df['time_numeric'] = (df.index - df.index[0]).total_seconds()
            
            X = df['time_numeric'].values.reshape(-1, 1)
            y = df['value'].values
            
            # 多項式特徴量を作成
            poly_features = PolynomialFeatures(degree=degree)
            X_poly = poly_features.fit_transform(X)
            
            # 多項式回帰
            model = LinearRegression()
            model.fit(X_poly, y)
            
            y_pred = model.predict(X_poly)
            r_squared = r2_score(y, y_pred)
            
            # 傾きを計算（最新点での微分）
            # 簡単な近似として最後の2点の傾きを使用
            if len(y) >= 2:
                slope = (y[-1] - y[-2]) / (df['time_numeric'].iloc[-1] - df['time_numeric'].iloc[-2])
            else:
                slope = 0.0
            
            # トレンド方向を判定
            if abs(slope) < 1e-6:
                trend_direction = "stable"
                trend_strength = 0.0
            elif slope > 0:
                trend_direction = "up"
                trend_strength = min(abs(slope) * 100, 1.0)
            else:
                trend_direction = "down"
                trend_strength = min(abs(slope) * 100, 1.0)
            
            return TrendAnalysisResult(
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                slope=slope,
                r_squared=r_squared
            )
            
        except Exception as e:
            logger.error(f"Error in polynomial trend analysis: {e}")
            raise
    
    async def _analyze_seasonal_trend(self, df: pd.DataFrame) -> TrendAnalysisResult:
        """季節性トレンド分析"""
        try:
            # 最低限のデータ数チェック
            if len(df) < 12:
                logger.warning("Insufficient data for seasonal analysis")
                return await self._analyze_linear_trend(df)
            
            values = df['value'].values
            
            # 季節性を検出（FFTを使用）
            fft = np.fft.fft(values)
            freqs = np.fft.fftfreq(len(values))
            
            # 最も強い周波数成分を見つける
            magnitudes = np.abs(fft)
            # DC成分を除外
            magnitudes[0] = 0
            
            peak_idx = np.argmax(magnitudes[:len(values)//2])
            if peak_idx > 0:
                seasonal_period = int(len(values) / peak_idx)
                seasonal_strength = magnitudes[peak_idx] / np.sum(magnitudes)
            else:
                seasonal_period = None
                seasonal_strength = 0.0
            
            # 基本的な線形トレンド分析も実行
            base_result = await self._analyze_linear_trend(df)
            
            # 季節性情報を追加
            base_result.seasonality_detected = seasonal_strength > 0.1
            base_result.seasonal_period = seasonal_period
            base_result.seasonal_strength = seasonal_strength
            
            return base_result
            
        except Exception as e:
            logger.error(f"Error in seasonal trend analysis: {e}")
            # フォールバックとして線形分析を実行
            return await self._analyze_linear_trend(df)
    
    async def detect_change_points(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        sensitivity: float = 0.1,
        farm_id: Optional[str] = None
    ) -> List[ChangePoint]:
        """
        変化点を検出
        """
        try:
            # データを取得
            aggregated_data = await self.aggregation_service.aggregate_sensor_data(
                measurement_type=measurement_type,
                start_time=start_time,
                end_time=end_time,
                window=AggregationWindow.HOUR,
                farm_id=farm_id
            )
            
            if len(aggregated_data) < 10:
                return []
            
            values = [data.value for data in aggregated_data]
            timestamps = [data.timestamp for data in aggregated_data]
            
            change_points = []
            
            # 移動平均との差を計算
            window_size = max(3, len(values) // 10)
            moving_avg = pd.Series(values).rolling(window=window_size, center=True).mean()
            
            # 変化点を検出
            for i in range(window_size, len(values) - window_size):
                before_values = values[i-window_size:i]
                after_values = values[i:i+window_size]
                
                before_mean = np.mean(before_values)
                after_mean = np.mean(after_values)
                
                change_magnitude = abs(after_mean - before_mean)
                relative_change = change_magnitude / (abs(before_mean) + 1e-6)
                
                if relative_change > sensitivity:
                    # 統計的有意性をテスト
                    t_stat, p_value = stats.ttest_ind(before_values, after_values)
                    confidence = 1.0 - p_value if p_value < 0.05 else 0.0
                    
                    if confidence > 0.8:
                        change_type = "increase" if after_mean > before_mean else "decrease"
                        
                        change_points.append(ChangePoint(
                            timestamp=timestamps[i],
                            change_magnitude=change_magnitude,
                            confidence=confidence,
                            change_type=change_type
                        ))
            
            logger.info(f"Detected {len(change_points)} change points")
            return change_points
            
        except Exception as e:
            logger.error(f"Error detecting change points: {e}")
            raise
    
    async def forecast_values(
        self,
        measurement_type: str,
        start_time: datetime,
        end_time: datetime,
        forecast_periods: int = 24,
        model_type: str = "linear",
        farm_id: Optional[str] = None
    ) -> ForecastResult:
        """
        将来値を予測
        """
        try:
            # 履歴データを取得
            aggregated_data = await self.aggregation_service.aggregate_sensor_data(
                measurement_type=measurement_type,
                start_time=start_time,
                end_time=end_time,
                window=AggregationWindow.HOUR,
                farm_id=farm_id
            )
            
            if len(aggregated_data) < 5:
                raise ValueError(f"Insufficient historical data for forecasting. Need at least 5 data points, got {len(aggregated_data)}")
            
            # データをPandasで処理
            df = pd.DataFrame([
                {"timestamp": data.timestamp, "value": data.value}
                for data in aggregated_data
            ])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # 時間間隔を計算
            time_intervals = df.index[1:] - df.index[:-1]
            avg_interval = time_intervals.mean()
            
            # 予測時刻を生成
            last_timestamp = df.index[-1]
            forecast_timestamps = [
                last_timestamp + (i + 1) * avg_interval
                for i in range(forecast_periods)
            ]
            
            # モデルに基づく予測
            if model_type == "linear":
                forecast_values, confidence_intervals = await self._linear_forecast(
                    df, forecast_periods
                )
            else:
                # デフォルトは線形予測
                forecast_values, confidence_intervals = await self._linear_forecast(
                    df, forecast_periods
                )
            
            # 精度メトリクスを計算（訓練データでの検証）
            accuracy_metrics = await self._calculate_forecast_accuracy(df, model_type)
            
            return ForecastResult(
                forecast_values=forecast_values,
                forecast_timestamps=forecast_timestamps,
                confidence_intervals=confidence_intervals,
                model_type=model_type,
                accuracy_metrics=accuracy_metrics
            )
            
        except Exception as e:
            logger.error(f"Error forecasting values: {e}")
            raise
    
    async def _linear_forecast(
        self, 
        df: pd.DataFrame, 
        periods: int
    ) -> Tuple[List[float], List[Tuple[float, float]]]:
        """線形モデルによる予測"""
        try:
            df['time_numeric'] = (df.index - df.index[0]).total_seconds()
            
            X = df['time_numeric'].values.reshape(-1, 1)
            y = df['value'].values
            
            # モデル訓練
            model = LinearRegression()
            model.fit(X, y)
            
            # 予測
            last_time = df['time_numeric'].iloc[-1]
            time_step = df['time_numeric'].iloc[-1] - df['time_numeric'].iloc[-2]
            
            forecast_times = [
                last_time + (i + 1) * time_step
                for i in range(periods)
            ]
            
            forecast_values = model.predict(np.array(forecast_times).reshape(-1, 1))
            
            # 信頼区間を計算
            y_pred = model.predict(X)
            residuals = y - y_pred
            mse = np.mean(residuals ** 2)
            std_error = np.sqrt(mse)
            
            confidence_intervals = [
                (val - 1.96 * std_error, val + 1.96 * std_error)
                for val in forecast_values
            ]
            
            return forecast_values.tolist(), confidence_intervals
            
        except Exception as e:
            logger.error(f"Error in linear forecast: {e}")
            raise
    
    async def _calculate_forecast_accuracy(
        self, 
        df: pd.DataFrame, 
        model_type: str
    ) -> Dict[str, float]:
        """予測精度を計算"""
        try:
            if len(df) < 20:
                return {"mse": 0.0, "mae": 0.0, "mape": 0.0}
            
            # 時系列分割で検証
            split_point = int(len(df) * 0.8)
            train_df = df.iloc[:split_point]
            test_df = df.iloc[split_point:]
            
            # 訓練データでモデル構築
            train_df['time_numeric'] = (train_df.index - train_df.index[0]).total_seconds()
            X_train = train_df['time_numeric'].values.reshape(-1, 1)
            y_train = train_df['value'].values
            
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # テストデータで予測
            test_df['time_numeric'] = (test_df.index - train_df.index[0]).total_seconds()
            X_test = test_df['time_numeric'].values.reshape(-1, 1)
            y_test = test_df['value'].values
            y_pred = model.predict(X_test)
            
            # 精度メトリクス計算
            mse = np.mean((y_test - y_pred) ** 2)
            mae = np.mean(np.abs(y_test - y_pred))
            mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-6))) * 100
            
            return {
                "mse": float(mse),
                "mae": float(mae),
                "mape": float(mape)
            }
            
        except Exception as e:
            logger.error(f"Error calculating forecast accuracy: {e}")
            return {"mse": 0.0, "mae": 0.0, "mape": 0.0}


# グローバルインスタンス
trend_analysis_engine = TrendAnalysisEngine()