"""
予測モデルサービス
リアルタイム予測、バッチ予測、モデル管理を提供
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from src.analytics.feature_engineering import (
    FeatureEngineeringService, FeatureType, WindowConfig, ScalingMethod
)
from src.analytics.ml_models import (
    MLModelService, ModelConfig, ModelType, TaskType, PredictionResult
)
from src.analytics.aggregation import DataAggregationService, AggregationWindow
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PredictionHorizon(str, Enum):
    """予測期間"""
    SHORT_TERM = "short_term"      # 1-6時間
    MEDIUM_TERM = "medium_term"    # 6-24時間
    LONG_TERM = "long_term"        # 1-7日


class PredictionRequest(BaseModel):
    """予測リクエスト"""
    measurement_types: List[str] = Field(..., description="対象測定タイプ")
    prediction_horizon: PredictionHorizon = Field(..., description="予測期間")
    prediction_periods: int = Field(default=24, description="予測ポイント数")
    farm_id: Optional[str] = None
    device_id: Optional[str] = None
    model_preferences: Optional[List[ModelType]] = None
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)


class PredictionResponse(BaseModel):
    """予測結果"""
    request_id: str
    measurement_type: str
    prediction_horizon: PredictionHorizon
    predictions: List[Dict[str, Any]]  # timestamp, value, confidence_interval
    model_info: Dict[str, Any]
    accuracy_metrics: Optional[Dict[str, float]] = None
    feature_importance: Optional[Dict[str, float]] = None
    generated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelPerformance(BaseModel):
    """モデル性能情報"""
    model_id: str
    model_type: ModelType
    measurement_type: str
    accuracy_score: float
    prediction_latency_ms: float
    last_updated: datetime
    prediction_count: int = 0
    error_rate: float = 0.0


class AutoMLConfig(BaseModel):
    """自動機械学習設定"""
    enable_auto_retraining: bool = Field(default=True)
    retraining_frequency_hours: int = Field(default=24)
    performance_threshold: float = Field(default=0.7)
    max_models_per_measurement: int = Field(default=5)
    feature_selection_methods: List[FeatureType] = Field(
        default=[FeatureType.STATISTICAL, FeatureType.TEMPORAL]
    )


class PredictionService:
    """予測サービス"""
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.ml_service = MLModelService()
        self.aggregation_service = DataAggregationService()
        
        # 各測定タイプに対する最適モデルを追跡
        self.best_models: Dict[str, str] = {}  # measurement_type -> model_id
        self.model_performances: Dict[str, ModelPerformance] = {}
        
        # AutoML設定
        self.automl_config = AutoMLConfig()
        
        # バックグラウンドタスク
        self._background_tasks: List[asyncio.Task] = []
    
    async def start_background_services(self):
        """バックグラウンドサービスを開始"""
        try:
            if self.automl_config.enable_auto_retraining:
                task = asyncio.create_task(self._auto_retraining_loop())
                self._background_tasks.append(task)
                logger.info("Started auto-retraining background service")
            
        except Exception as e:
            logger.error(f"Error starting background services: {e}")
    
    async def stop_background_services(self):
        """バックグラウンドサービスを停止"""
        try:
            for task in self._background_tasks:
                task.cancel()
            
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()
            logger.info("Stopped background services")
            
        except Exception as e:
            logger.error(f"Error stopping background services: {e}")
    
    async def predict_single_measurement(
        self,
        request: PredictionRequest,
        measurement_type: str
    ) -> PredictionResponse:
        """
        単一測定タイプの予測
        """
        try:
            request_id = f"pred_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{measurement_type}"
            
            # 最適モデルを取得
            model_id = await self._get_best_model(measurement_type, request.model_preferences)
            
            if not model_id:
                # モデルが存在しない場合は訓練
                model_id = await self._train_prediction_model(
                    measurement_type, request.farm_id, request.device_id
                )
                
                if not model_id:
                    raise ValueError(f"Failed to create prediction model for {measurement_type}")
            
            # 予測データを準備
            prediction_data = await self._prepare_prediction_data(
                measurement_type, request.farm_id, request.device_id, request.prediction_periods
            )
            
            # 予測実行
            start_time = datetime.now()
            prediction_result = await self.ml_service.predict(model_id, prediction_data)
            prediction_latency = (datetime.now() - start_time).total_seconds() * 1000
            
            # 結果を整形
            predictions = await self._format_prediction_results(
                prediction_result, request.prediction_periods, measurement_type
            )
            
            # モデル性能を更新
            await self._update_model_performance(model_id, measurement_type, prediction_latency)
            
            # モデル情報を取得
            model_info = await self.ml_service.get_model_info(model_id)
            
            response = PredictionResponse(
                request_id=request_id,
                measurement_type=measurement_type,
                prediction_horizon=request.prediction_horizon,
                predictions=predictions,
                model_info={
                    "model_id": model_id,
                    "model_type": model_info.model_type.value if model_info else "unknown",
                    "trained_at": model_info.trained_at.isoformat() if model_info else None,
                    "metrics": model_info.metrics.model_dump() if model_info else None
                },
                feature_importance=prediction_result.feature_importance,
                generated_at=datetime.now(timezone.utc),
                metadata={
                    "farm_id": request.farm_id,
                    "device_id": request.device_id,
                    "prediction_latency_ms": prediction_latency,
                    "confidence_level": request.confidence_level
                }
            )
            
            logger.info(f"Generated prediction for {measurement_type}: {request_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error predicting {measurement_type}: {e}")
            raise
    
    async def predict_multiple_measurements(
        self,
        request: PredictionRequest
    ) -> List[PredictionResponse]:
        """
        複数測定タイプの予測
        """
        try:
            # 並行して予測を実行
            tasks = [
                self.predict_single_measurement(request, measurement_type)
                for measurement_type in request.measurement_types
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 成功した結果のみを返す
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error predicting {request.measurement_types[i]}: {result}")
                else:
                    successful_results.append(result)
            
            return successful_results
            
        except Exception as e:
            logger.error(f"Error predicting multiple measurements: {e}")
            raise
    
    async def detect_anomalies_realtime(
        self,
        measurement_types: List[str],
        time_window_minutes: int = 60,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        リアルタイム異常検知
        """
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=time_window_minutes)
            
            anomalies = {}
            
            for measurement_type in measurement_types:
                # 最新データで特徴量を抽出
                feature_set = await self.feature_service.extract_features(
                    measurement_types=[measurement_type],
                    start_time=start_time,
                    end_time=end_time,
                    feature_types=[FeatureType.STATISTICAL, FeatureType.TEMPORAL],
                    window_config=WindowConfig(window_size=10, step_size=1),
                    farm_id=farm_id,
                    device_id=device_id
                )
                
                if not feature_set.feature_values:
                    continue
                
                # 異常検知モデルを取得
                anomaly_model_id = await self._get_anomaly_model(measurement_type)
                
                if anomaly_model_id:
                    # 異常検知実行
                    feature_data = np.array(feature_set.feature_values)
                    prediction_result = await self.ml_service.predict(anomaly_model_id, feature_data)
                    
                    # 異常判定
                    anomaly_count = np.sum(np.array(prediction_result.predictions) == -1)
                    anomaly_ratio = anomaly_count / len(prediction_result.predictions)
                    
                    anomalies[measurement_type] = {
                        "anomaly_detected": anomaly_ratio > 0.1,  # 10%以上が異常
                        "anomaly_ratio": anomaly_ratio,
                        "anomaly_count": anomaly_count,
                        "total_samples": len(prediction_result.predictions),
                        "anomaly_scores": prediction_result.anomaly_scores,
                        "timestamps": [ts.isoformat() for ts in feature_set.timestamps]
                    }
                else:
                    logger.warning(f"No anomaly detection model for {measurement_type}")
            
            return {
                "detection_time": end_time.isoformat(),
                "time_window_minutes": time_window_minutes,
                "farm_id": farm_id,
                "device_id": device_id,
                "anomalies": anomalies
            }
            
        except Exception as e:
            logger.error(f"Error in realtime anomaly detection: {e}")
            raise
    
    async def _get_best_model(
        self,
        measurement_type: str,
        model_preferences: Optional[List[ModelType]] = None
    ) -> Optional[str]:
        """最適モデルを取得"""
        try:
            # 既存の最適モデルをチェック
            if measurement_type in self.best_models:
                model_id = self.best_models[measurement_type]
                model_info = await self.ml_service.get_model_info(model_id)
                if model_info:
                    return model_id
            
            # すべてのモデルから検索
            all_models = await self.ml_service.list_models()
            
            # 該当する測定タイプの予測モデルを抽出
            candidate_models = [
                model for model in all_models
                if (model.task_type in [TaskType.REGRESSION, TaskType.FORECASTING] and
                    model.target_variable == measurement_type)
            ]
            
            if not candidate_models:
                return None
            
            # モデル優先度に基づいて選択
            if model_preferences:
                for preferred_type in model_preferences:
                    for model in candidate_models:
                        if model.model_type == preferred_type:
                            self.best_models[measurement_type] = model.model_id
                            return model.model_id
            
            # 性能に基づいて選択
            best_model = max(candidate_models, key=lambda m: m.metrics.r2_score or 0)
            self.best_models[measurement_type] = best_model.model_id
            return best_model.model_id
            
        except Exception as e:
            logger.error(f"Error getting best model for {measurement_type}: {e}")
            return None
    
    async def _get_anomaly_model(self, measurement_type: str) -> Optional[str]:
        """異常検知モデルを取得"""
        try:
            all_models = await self.ml_service.list_models()
            
            # 異常検知モデルを検索
            anomaly_models = [
                model for model in all_models
                if model.task_type == TaskType.ANOMALY_DETECTION
            ]
            
            if anomaly_models:
                # 最新のモデルを返す
                latest_model = max(anomaly_models, key=lambda m: m.trained_at)
                return latest_model.model_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting anomaly model: {e}")
            return None
    
    async def _train_prediction_model(
        self,
        measurement_type: str,
        farm_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Optional[str]:
        """予測モデルを訓練"""
        try:
            logger.info(f"Training new prediction model for {measurement_type}")
            
            # 過去1週間のデータで特徴量を抽出
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            feature_set = await self.feature_service.extract_features(
                measurement_types=[measurement_type],
                start_time=start_time,
                end_time=end_time,
                feature_types=[FeatureType.STATISTICAL, FeatureType.TEMPORAL, FeatureType.SPECTRAL],
                window_config=WindowConfig(window_size=24, step_size=1),  # 24時間窓
                farm_id=farm_id,
                device_id=device_id,
                scaling_method=ScalingMethod.STANDARD
            )
            
            if not feature_set.feature_values or len(feature_set.feature_values) < 100:
                logger.warning(f"Insufficient data for training {measurement_type} model")
                return None
            
            # 訓練データを準備
            training_data = await self.feature_service.prepare_training_data(
                feature_set=feature_set,
                target_measurement_type=measurement_type,
                prediction_horizon=1
            )
            
            # モデル設定
            model_config = ModelConfig(
                model_type=ModelType.RANDOM_FOREST_REGRESSOR,
                task_type=TaskType.REGRESSION,
                hyperparameters={
                    "n_estimators": 100,
                    "max_depth": 10,
                    "random_state": 42
                }
            )
            
            # モデル訓練
            trained_model = await self.ml_service.train_prediction_model(
                training_data, model_config
            )
            
            # 最適モデルとして登録
            self.best_models[measurement_type] = trained_model.model_id
            
            logger.info(f"Successfully trained model {trained_model.model_id} for {measurement_type}")
            return trained_model.model_id
            
        except Exception as e:
            logger.error(f"Error training prediction model for {measurement_type}: {e}")
            return None
    
    async def _prepare_prediction_data(
        self,
        measurement_type: str,
        farm_id: Optional[str],
        device_id: Optional[str],
        periods: int
    ) -> np.ndarray:
        """予測用データを準備"""
        try:
            # 最新のデータを取得
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)  # 24時間分
            
            feature_set = await self.feature_service.extract_features(
                measurement_types=[measurement_type],
                start_time=start_time,
                end_time=end_time,
                feature_types=[FeatureType.STATISTICAL, FeatureType.TEMPORAL, FeatureType.SPECTRAL],
                window_config=WindowConfig(window_size=24, step_size=1),
                farm_id=farm_id,
                device_id=device_id,
                scaling_method=ScalingMethod.STANDARD
            )
            
            if not feature_set.feature_values:
                raise ValueError("No recent data available for prediction")
            
            # 最新の特徴量を使用
            latest_features = np.array(feature_set.feature_values[-periods:])
            
            # データが不足している場合は最新の特徴量を複製
            if len(latest_features) < periods:
                latest_feature = feature_set.feature_values[-1]
                latest_features = np.array([latest_feature] * periods)
            
            return latest_features
            
        except Exception as e:
            logger.error(f"Error preparing prediction data: {e}")
            raise
    
    async def _format_prediction_results(
        self,
        prediction_result: PredictionResult,
        periods: int,
        measurement_type: str
    ) -> List[Dict[str, Any]]:
        """予測結果を整形"""
        try:
            current_time = datetime.now(timezone.utc)
            predictions = []
            
            for i, value in enumerate(prediction_result.predictions[:periods]):
                timestamp = current_time + timedelta(hours=i+1)
                
                # 信頼区間（簡易実装）
                if prediction_result.confidence_intervals:
                    confidence_interval = prediction_result.confidence_intervals[i]
                else:
                    # 標準偏差の推定値を使用
                    std_estimate = np.std(prediction_result.predictions) * 0.1
                    confidence_interval = (value - std_estimate, value + std_estimate)
                
                predictions.append({
                    "timestamp": timestamp.isoformat(),
                    "value": float(value),
                    "confidence_interval": {
                        "lower": float(confidence_interval[0]),
                        "upper": float(confidence_interval[1])
                    },
                    "measurement_type": measurement_type
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error formatting prediction results: {e}")
            raise
    
    async def _update_model_performance(
        self,
        model_id: str,
        measurement_type: str,
        latency_ms: float
    ):
        """モデル性能を更新"""
        try:
            if model_id not in self.model_performances:
                model_info = await self.ml_service.get_model_info(model_id)
                
                self.model_performances[model_id] = ModelPerformance(
                    model_id=model_id,
                    model_type=model_info.model_type if model_info else ModelType.RANDOM_FOREST_REGRESSOR,
                    measurement_type=measurement_type,
                    accuracy_score=model_info.metrics.r2_score or 0.0 if model_info else 0.0,
                    prediction_latency_ms=latency_ms,
                    last_updated=datetime.now(timezone.utc)
                )
            else:
                performance = self.model_performances[model_id]
                performance.prediction_count += 1
                performance.prediction_latency_ms = (
                    performance.prediction_latency_ms * 0.9 + latency_ms * 0.1
                )  # 移動平均
                performance.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error updating model performance: {e}")
    
    async def _auto_retraining_loop(self):
        """自動再訓練ループ"""
        try:
            while True:
                await asyncio.sleep(self.automl_config.retraining_frequency_hours * 3600)
                
                logger.info("Starting auto-retraining process")
                
                # 性能が低下したモデルを再訓練
                for model_id, performance in self.model_performances.items():
                    if performance.accuracy_score < self.automl_config.performance_threshold:
                        logger.info(f"Retraining model {model_id} due to low performance")
                        
                        try:
                            new_model_id = await self._train_prediction_model(
                                performance.measurement_type
                            )
                            
                            if new_model_id:
                                # 古いモデルを削除
                                await self.ml_service.delete_model(model_id)
                                
                                # 新しいモデルに更新
                                self.best_models[performance.measurement_type] = new_model_id
                                
                                logger.info(f"Successfully retrained model for {performance.measurement_type}")
                            
                        except Exception as e:
                            logger.error(f"Error retraining model {model_id}: {e}")
                
                logger.info("Completed auto-retraining process")
                
        except asyncio.CancelledError:
            logger.info("Auto-retraining loop cancelled")
        except Exception as e:
            logger.error(f"Error in auto-retraining loop: {e}")
    
    async def get_model_performance_summary(self) -> Dict[str, Any]:
        """モデル性能サマリーを取得"""
        try:
            summary = {
                "total_models": len(self.model_performances),
                "models": []
            }
            
            for model_id, performance in self.model_performances.items():
                summary["models"].append(performance.model_dump())
            
            # 平均性能を計算
            if self.model_performances:
                avg_accuracy = np.mean([p.accuracy_score for p in self.model_performances.values()])
                avg_latency = np.mean([p.prediction_latency_ms for p in self.model_performances.values()])
                
                summary["average_accuracy"] = float(avg_accuracy)
                summary["average_latency_ms"] = float(avg_latency)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting model performance summary: {e}")
            raise


# グローバルインスタンス
prediction_service = PredictionService()