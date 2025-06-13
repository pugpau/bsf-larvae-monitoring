"""
モデル訓練・評価パイプライン
自動化された機械学習パイプライン
"""

import logging
import asyncio
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from src.analytics.feature_engineering import (
    FeatureEngineeringService, FeatureType, WindowConfig, ScalingMethod
)
from src.analytics.ml_models import (
    MLModelService, ModelConfig, ModelType, TaskType, TrainedModel
)
from src.analytics.aggregation import DataAggregationService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PipelineStage(str, Enum):
    """パイプラインのステージ"""
    DATA_COLLECTION = "data_collection"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_VALIDATION = "model_validation"
    MODEL_DEPLOYMENT = "model_deployment"


class PipelineStatus(str, Enum):
    """パイプラインステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingConfig(BaseModel):
    """訓練設定"""
    measurement_types: List[str] = Field(..., description="対象測定タイプ")
    training_period_days: int = Field(default=30, description="訓練期間（日）")
    test_split_ratio: float = Field(default=0.2, ge=0.1, le=0.4)
    feature_types: List[FeatureType] = Field(
        default=[FeatureType.STATISTICAL, FeatureType.TEMPORAL, FeatureType.SPECTRAL]
    )
    window_config: WindowConfig = Field(default=WindowConfig(window_size=24, step_size=1))
    scaling_method: ScalingMethod = Field(default=ScalingMethod.STANDARD)
    
    # モデル設定
    model_types: List[ModelType] = Field(
        default=[ModelType.RANDOM_FOREST_REGRESSOR, ModelType.LINEAR_REGRESSION]
    )
    hyperparameter_tuning: bool = Field(default=True)
    cross_validation_folds: int = Field(default=5)
    
    # フィルター設定
    farm_id: Optional[str] = None
    device_id: Optional[str] = None
    
    # 異常検知設定
    include_anomaly_detection: bool = Field(default=True)
    contamination_rate: float = Field(default=0.1, ge=0.01, le=0.3)


class PipelineResult(BaseModel):
    """パイプライン実行結果"""
    pipeline_id: str
    config: TrainingConfig
    status: PipelineStatus
    
    # 各ステージの結果
    stages: Dict[PipelineStage, Dict[str, Any]] = Field(default_factory=dict)
    
    # 訓練されたモデル
    trained_models: List[str] = Field(default_factory=list)  # model_ids
    best_models: Dict[str, str] = Field(default_factory=dict)  # measurement_type -> model_id
    
    # 実行時間
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # エラー情報
    error_message: Optional[str] = None
    error_stage: Optional[PipelineStage] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelEvaluationReport(BaseModel):
    """モデル評価レポート"""
    model_id: str
    model_type: ModelType
    measurement_type: str
    
    # 性能メトリクス
    metrics: Dict[str, float]
    
    # 特徴量重要度
    feature_importance: Optional[Dict[str, float]] = None
    
    # クロスバリデーション結果
    cv_scores: List[float] = Field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0
    
    # 予測例
    prediction_samples: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 評価時刻
    evaluated_at: datetime


class TrainingPipeline:
    """機械学習訓練パイプライン"""
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.ml_service = MLModelService()
        self.aggregation_service = DataAggregationService()
        
        # パイプライン実行履歴
        self.pipeline_results: Dict[str, PipelineResult] = {}
        
        # 評価レポート
        self.evaluation_reports: Dict[str, ModelEvaluationReport] = {}
    
    async def run_training_pipeline(
        self,
        config: TrainingConfig
    ) -> PipelineResult:
        """
        訓練パイプラインを実行
        """
        try:
            pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # パイプライン結果を初期化
            result = PipelineResult(
                pipeline_id=pipeline_id,
                config=config,
                status=PipelineStatus.RUNNING,
                started_at=datetime.now(timezone.utc)
            )
            
            self.pipeline_results[pipeline_id] = result
            
            logger.info(f"Starting training pipeline: {pipeline_id}")
            
            # ステージ1: データ収集
            await self._run_data_collection_stage(result)
            
            # ステージ2: 特徴量エンジニアリング
            await self._run_feature_engineering_stage(result)
            
            # ステージ3: モデル訓練
            await self._run_model_training_stage(result)
            
            # ステージ4: モデル評価
            await self._run_model_evaluation_stage(result)
            
            # ステージ5: モデル検証
            await self._run_model_validation_stage(result)
            
            # ステージ6: モデルデプロイ（最良モデル選択）
            await self._run_model_deployment_stage(result)
            
            # パイプライン完了
            result.status = PipelineStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            logger.info(f"Training pipeline completed: {pipeline_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in training pipeline {pipeline_id}: {e}")
            
            result.status = PipelineStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.completed_at - result.started_at).total_seconds()
            
            raise
    
    async def _run_data_collection_stage(self, result: PipelineResult):
        """データ収集ステージ"""
        try:
            logger.info("Running data collection stage")
            
            config = result.config
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=config.training_period_days)
            
            stage_result = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "measurement_types": config.measurement_types,
                "data_availability": {}
            }
            
            # 各測定タイプのデータ可用性をチェック
            for measurement_type in config.measurement_types:
                aggregated_data = await self.aggregation_service.aggregate_sensor_data(
                    measurement_type=measurement_type,
                    start_time=start_time,
                    end_time=end_time,
                    window=AggregationWindow.HOUR,
                    farm_id=config.farm_id,
                    device_id=config.device_id
                )
                
                stage_result["data_availability"][measurement_type] = {
                    "data_points": len(aggregated_data),
                    "coverage_hours": len(aggregated_data),
                    "sufficient_data": len(aggregated_data) >= 100
                }
            
            result.stages[PipelineStage.DATA_COLLECTION] = stage_result
            logger.info("Data collection stage completed")
            
        except Exception as e:
            logger.error(f"Error in data collection stage: {e}")
            result.error_stage = PipelineStage.DATA_COLLECTION
            raise
    
    async def _run_feature_engineering_stage(self, result: PipelineResult):
        """特徴量エンジニアリングステージ"""
        try:
            logger.info("Running feature engineering stage")
            
            config = result.config
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=config.training_period_days)
            
            stage_result = {
                "feature_sets": {},
                "training_datasets": {}
            }
            
            # 各測定タイプの特徴量を抽出
            for measurement_type in config.measurement_types:
                # データ可用性チェック
                data_info = result.stages[PipelineStage.DATA_COLLECTION]["data_availability"][measurement_type]
                if not data_info["sufficient_data"]:
                    logger.warning(f"Insufficient data for {measurement_type}, skipping")
                    continue
                
                # 特徴量抽出
                feature_set = await self.feature_service.extract_features(
                    measurement_types=[measurement_type],
                    start_time=start_time,
                    end_time=end_time,
                    feature_types=config.feature_types,
                    window_config=config.window_config,
                    farm_id=config.farm_id,
                    device_id=config.device_id,
                    scaling_method=config.scaling_method
                )
                
                if not feature_set.feature_values:
                    logger.warning(f"No features extracted for {measurement_type}")
                    continue
                
                # 訓練データ準備
                training_data = await self.feature_service.prepare_training_data(
                    feature_set=feature_set,
                    target_measurement_type=measurement_type,
                    prediction_horizon=1,
                    test_split_ratio=config.test_split_ratio
                )
                
                stage_result["feature_sets"][measurement_type] = {
                    "feature_count": len(feature_set.feature_names),
                    "sample_count": len(feature_set.feature_values),
                    "feature_names": feature_set.feature_names[:10]  # 最初の10個のみ記録
                }
                
                stage_result["training_datasets"][measurement_type] = {
                    "train_samples": len(training_data["X_train"]),
                    "test_samples": len(training_data["X_test"]),
                    "feature_count": len(training_data["feature_names"])
                }
                
                # 訓練データを一時保存
                result.metadata[f"training_data_{measurement_type}"] = training_data
                result.metadata[f"feature_set_{measurement_type}"] = feature_set
            
            result.stages[PipelineStage.FEATURE_ENGINEERING] = stage_result
            logger.info("Feature engineering stage completed")
            
        except Exception as e:
            logger.error(f"Error in feature engineering stage: {e}")
            result.error_stage = PipelineStage.FEATURE_ENGINEERING
            raise
    
    async def _run_model_training_stage(self, result: PipelineResult):
        """モデル訓練ステージ"""
        try:
            logger.info("Running model training stage")
            
            config = result.config
            stage_result = {
                "trained_models": {},
                "training_errors": {}
            }
            
            # 各測定タイプとモデルタイプの組み合わせで訓練
            for measurement_type in config.measurement_types:
                training_data_key = f"training_data_{measurement_type}"
                if training_data_key not in result.metadata:
                    continue
                
                training_data = result.metadata[training_data_key]
                stage_result["trained_models"][measurement_type] = {}
                
                for model_type in config.model_types:
                    try:
                        # 予測モデル訓練
                        model_config = ModelConfig(
                            model_type=model_type,
                            task_type=TaskType.REGRESSION,
                            hyperparameters=self._get_default_hyperparameters(model_type)
                        )
                        
                        trained_model = await self.ml_service.train_prediction_model(
                            training_data, model_config
                        )
                        
                        result.trained_models.append(trained_model.model_id)
                        stage_result["trained_models"][measurement_type][model_type.value] = {
                            "model_id": trained_model.model_id,
                            "r2_score": trained_model.metrics.r2_score,
                            "mse": trained_model.metrics.mse,
                            "mae": trained_model.metrics.mae
                        }
                        
                        logger.info(f"Trained {model_type.value} for {measurement_type}")
                        
                    except Exception as e:
                        error_msg = f"Error training {model_type.value} for {measurement_type}: {e}"
                        logger.error(error_msg)
                        stage_result["training_errors"][f"{measurement_type}_{model_type.value}"] = error_msg
                
                # 異常検知モデル訓練
                if config.include_anomaly_detection:
                    try:
                        feature_set = result.metadata[f"feature_set_{measurement_type}"]
                        
                        anomaly_config = ModelConfig(
                            model_type=ModelType.ISOLATION_FOREST,
                            task_type=TaskType.ANOMALY_DETECTION,
                            hyperparameters={
                                "contamination": config.contamination_rate,
                                "n_estimators": 100,
                                "random_state": 42
                            }
                        )
                        
                        anomaly_model = await self.ml_service.train_anomaly_detection_model(
                            feature_set, anomaly_config, config.contamination_rate
                        )
                        
                        result.trained_models.append(anomaly_model.model_id)
                        stage_result["trained_models"][measurement_type]["anomaly_detection"] = {
                            "model_id": anomaly_model.model_id,
                            "model_type": "isolation_forest"
                        }
                        
                        logger.info(f"Trained anomaly detection for {measurement_type}")
                        
                    except Exception as e:
                        error_msg = f"Error training anomaly detection for {measurement_type}: {e}"
                        logger.error(error_msg)
                        stage_result["training_errors"][f"{measurement_type}_anomaly"] = error_msg
            
            result.stages[PipelineStage.MODEL_TRAINING] = stage_result
            logger.info("Model training stage completed")
            
        except Exception as e:
            logger.error(f"Error in model training stage: {e}")
            result.error_stage = PipelineStage.MODEL_TRAINING
            raise
    
    async def _run_model_evaluation_stage(self, result: PipelineResult):
        """モデル評価ステージ"""
        try:
            logger.info("Running model evaluation stage")
            
            stage_result = {
                "evaluations": {},
                "performance_comparison": {}
            }
            
            # 訓練された各モデルを評価
            for model_id in result.trained_models:
                try:
                    model_info = await self.ml_service.get_model_info(model_id)
                    if not model_info:
                        continue
                    
                    evaluation_report = await self._evaluate_model(model_info, result)
                    self.evaluation_reports[model_id] = evaluation_report
                    
                    stage_result["evaluations"][model_id] = evaluation_report.model_dump()
                    
                except Exception as e:
                    logger.error(f"Error evaluating model {model_id}: {e}")
            
            # 性能比較
            stage_result["performance_comparison"] = await self._compare_model_performance(result)
            
            result.stages[PipelineStage.MODEL_EVALUATION] = stage_result
            logger.info("Model evaluation stage completed")
            
        except Exception as e:
            logger.error(f"Error in model evaluation stage: {e}")
            result.error_stage = PipelineStage.MODEL_EVALUATION
            raise
    
    async def _run_model_validation_stage(self, result: PipelineResult):
        """モデル検証ステージ"""
        try:
            logger.info("Running model validation stage")
            
            stage_result = {
                "validation_results": {},
                "passed_models": [],
                "failed_models": []
            }
            
            # 各モデルの検証
            for model_id in result.trained_models:
                try:
                    validation_result = await self._validate_model(model_id, result)
                    stage_result["validation_results"][model_id] = validation_result
                    
                    if validation_result["passed"]:
                        stage_result["passed_models"].append(model_id)
                    else:
                        stage_result["failed_models"].append(model_id)
                        
                except Exception as e:
                    logger.error(f"Error validating model {model_id}: {e}")
                    stage_result["failed_models"].append(model_id)
            
            result.stages[PipelineStage.MODEL_VALIDATION] = stage_result
            logger.info("Model validation stage completed")
            
        except Exception as e:
            logger.error(f"Error in model validation stage: {e}")
            result.error_stage = PipelineStage.MODEL_VALIDATION
            raise
    
    async def _run_model_deployment_stage(self, result: PipelineResult):
        """モデルデプロイステージ（最良モデル選択）"""
        try:
            logger.info("Running model deployment stage")
            
            stage_result = {
                "selected_models": {},
                "deployment_status": {}
            }
            
            # 各測定タイプで最良モデルを選択
            validation_results = result.stages[PipelineStage.MODEL_VALIDATION]
            passed_models = validation_results["passed_models"]
            
            for measurement_type in result.config.measurement_types:
                best_model_id = None
                best_score = -float('inf')
                
                # 通過したモデルから最良のものを選択
                for model_id in passed_models:
                    if model_id in self.evaluation_reports:
                        report = self.evaluation_reports[model_id]
                        if report.measurement_type == measurement_type:
                            # R2スコアまたは他の適切なメトリクスで比較
                            score = report.metrics.get("r2_score", 0)
                            if score > best_score:
                                best_score = score
                                best_model_id = model_id
                
                if best_model_id:
                    result.best_models[measurement_type] = best_model_id
                    stage_result["selected_models"][measurement_type] = {
                        "model_id": best_model_id,
                        "score": best_score
                    }
                    
                    stage_result["deployment_status"][measurement_type] = "deployed"
                    logger.info(f"Selected model {best_model_id} for {measurement_type}")
                else:
                    stage_result["deployment_status"][measurement_type] = "no_suitable_model"
                    logger.warning(f"No suitable model found for {measurement_type}")
            
            result.stages[PipelineStage.MODEL_DEPLOYMENT] = stage_result
            logger.info("Model deployment stage completed")
            
        except Exception as e:
            logger.error(f"Error in model deployment stage: {e}")
            result.error_stage = PipelineStage.MODEL_DEPLOYMENT
            raise
    
    def _get_default_hyperparameters(self, model_type: ModelType) -> Dict[str, Any]:
        """デフォルトハイパーパラメータを取得"""
        defaults = {
            ModelType.RANDOM_FOREST_REGRESSOR: {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            },
            ModelType.LINEAR_REGRESSION: {},
            ModelType.MLP_REGRESSOR: {
                "hidden_layer_sizes": (100, 50),
                "activation": "relu",
                "solver": "adam",
                "max_iter": 200,
                "random_state": 42
            }
        }
        
        return defaults.get(model_type, {})
    
    async def _evaluate_model(self, model_info: TrainedModel, result: PipelineResult) -> ModelEvaluationReport:
        """モデルを評価"""
        try:
            report = ModelEvaluationReport(
                model_id=model_info.model_id,
                model_type=model_info.model_type,
                measurement_type=model_info.target_variable or "unknown",
                metrics=model_info.metrics.model_dump(),
                evaluated_at=datetime.now(timezone.utc)
            )
            
            # クロスバリデーション結果
            if model_info.metrics.cross_val_scores:
                report.cv_scores = model_info.metrics.cross_val_scores
                report.cv_mean = float(np.mean(model_info.metrics.cross_val_scores))
                report.cv_std = float(np.std(model_info.metrics.cross_val_scores))
            
            return report
            
        except Exception as e:
            logger.error(f"Error evaluating model {model_info.model_id}: {e}")
            raise
    
    async def _compare_model_performance(self, result: PipelineResult) -> Dict[str, Any]:
        """モデル性能を比較"""
        try:
            comparison = {
                "by_measurement_type": {},
                "overall_summary": {}
            }
            
            # 測定タイプ別の比較
            for measurement_type in result.config.measurement_types:
                models_for_type = []
                
                for model_id in result.trained_models:
                    if model_id in self.evaluation_reports:
                        report = self.evaluation_reports[model_id]
                        if report.measurement_type == measurement_type:
                            models_for_type.append({
                                "model_id": model_id,
                                "model_type": report.model_type.value,
                                "r2_score": report.metrics.get("r2_score", 0),
                                "mse": report.metrics.get("mse", float('inf')),
                                "mae": report.metrics.get("mae", float('inf'))
                            })
                
                # R2スコアでソート
                models_for_type.sort(key=lambda x: x["r2_score"], reverse=True)
                comparison["by_measurement_type"][measurement_type] = models_for_type
            
            # 全体サマリー
            all_r2_scores = []
            for report in self.evaluation_reports.values():
                if "r2_score" in report.metrics:
                    all_r2_scores.append(report.metrics["r2_score"])
            
            if all_r2_scores:
                comparison["overall_summary"] = {
                    "average_r2_score": float(np.mean(all_r2_scores)),
                    "best_r2_score": float(np.max(all_r2_scores)),
                    "worst_r2_score": float(np.min(all_r2_scores)),
                    "total_models": len(all_r2_scores)
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing model performance: {e}")
            return {}
    
    async def _validate_model(self, model_id: str, result: PipelineResult) -> Dict[str, Any]:
        """モデルを検証"""
        try:
            validation_result = {
                "passed": False,
                "checks": {},
                "score": 0.0
            }
            
            if model_id not in self.evaluation_reports:
                validation_result["checks"]["evaluation_exists"] = False
                return validation_result
            
            report = self.evaluation_reports[model_id]
            validation_result["checks"]["evaluation_exists"] = True
            
            # R2スコアチェック（回帰モデル）
            if "r2_score" in report.metrics:
                r2_score = report.metrics["r2_score"]
                validation_result["checks"]["r2_score"] = r2_score
                validation_result["checks"]["r2_threshold_passed"] = r2_score > 0.5
            
            # MSEチェック
            if "mse" in report.metrics:
                mse = report.metrics["mse"]
                validation_result["checks"]["mse"] = mse
                validation_result["checks"]["mse_reasonable"] = mse < 100  # 適当な閾値
            
            # クロスバリデーションの安定性
            if report.cv_scores:
                cv_std = report.cv_std
                validation_result["checks"]["cv_std"] = cv_std
                validation_result["checks"]["cv_stable"] = cv_std < 0.1
            
            # 総合判定
            checks = validation_result["checks"]
            passed_count = sum(1 for key, value in checks.items() 
                             if key.endswith("_passed") or key.endswith("_reasonable") or key.endswith("_stable"))
            total_checks = len([key for key in checks.keys() 
                               if key.endswith("_passed") or key.endswith("_reasonable") or key.endswith("_stable")])
            
            if total_checks > 0:
                validation_result["score"] = passed_count / total_checks
                validation_result["passed"] = validation_result["score"] >= 0.7
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating model {model_id}: {e}")
            return {"passed": False, "error": str(e)}
    
    async def get_pipeline_status(self, pipeline_id: str) -> Optional[PipelineResult]:
        """パイプラインステータスを取得"""
        return self.pipeline_results.get(pipeline_id)
    
    async def list_pipelines(self) -> List[PipelineResult]:
        """すべてのパイプラインを一覧"""
        return list(self.pipeline_results.values())
    
    async def get_evaluation_report(self, model_id: str) -> Optional[ModelEvaluationReport]:
        """評価レポートを取得"""
        return self.evaluation_reports.get(model_id)


# グローバルインスタンス
training_pipeline = TrainingPipeline()