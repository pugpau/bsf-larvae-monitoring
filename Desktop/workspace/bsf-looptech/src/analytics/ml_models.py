"""
機械学習モデル実装
異常検知と予測のための機械学習モデル
"""

import logging
import pickle
import json
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

# 機械学習ライブラリ
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.svm import OneClassSVM
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score,
    classification_report, confusion_matrix
)
from sklearn.model_selection import cross_val_score, GridSearchCV

from src.analytics.feature_engineering import FeatureEngineeringService, FeatureSet
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ModelType(str, Enum):
    """モデルの種類"""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"
    DBSCAN = "dbscan"
    RANDOM_FOREST_CLASSIFIER = "random_forest_classifier"
    RANDOM_FOREST_REGRESSOR = "random_forest_regressor"
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    MLP_CLASSIFIER = "mlp_classifier"
    MLP_REGRESSOR = "mlp_regressor"


class TaskType(str, Enum):
    """タスクの種類"""
    ANOMALY_DETECTION = "anomaly_detection"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    FORECASTING = "forecasting"


class ModelMetrics(BaseModel):
    """モデル評価メトリクス"""
    task_type: TaskType
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    mse: Optional[float] = None
    mae: Optional[float] = None
    r2_score: Optional[float] = None
    cross_val_scores: Optional[List[float]] = None
    confusion_matrix: Optional[List[List[int]]] = None
    classification_report: Optional[Dict[str, Any]] = None


class ModelConfig(BaseModel):
    """モデル設定"""
    model_type: ModelType
    task_type: TaskType
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    feature_selection: Optional[List[str]] = None
    target_variable: Optional[str] = None


class TrainedModel(BaseModel):
    """訓練済みモデル"""
    model_id: str
    model_type: ModelType
    task_type: TaskType
    trained_at: datetime
    feature_names: List[str]
    target_variable: Optional[str] = None
    metrics: ModelMetrics
    hyperparameters: Dict[str, Any]
    model_file_path: str
    scaler_file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PredictionResult(BaseModel):
    """予測結果"""
    predictions: List[float]
    probabilities: Optional[List[List[float]]] = None
    anomaly_scores: Optional[List[float]] = None
    confidence_intervals: Optional[List[Tuple[float, float]]] = None
    feature_importance: Optional[Dict[str, float]] = None
    model_id: str
    predicted_at: datetime


class MLModelService:
    """機械学習モデルサービス"""
    
    def __init__(self):
        self.feature_service = FeatureEngineeringService()
        self.models_dir = Path("/tmp/bsf_ml_models")
        self.models_dir.mkdir(exist_ok=True)
        self.trained_models: Dict[str, TrainedModel] = {}
    
    async def train_anomaly_detection_model(
        self,
        feature_set: FeatureSet,
        model_config: ModelConfig,
        contamination: float = 0.1
    ) -> TrainedModel:
        """
        異常検知モデルを訓練
        """
        try:
            if model_config.task_type != TaskType.ANOMALY_DETECTION:
                raise ValueError("Task type must be ANOMALY_DETECTION")
            
            X = np.array(feature_set.feature_values)
            if len(X) == 0:
                raise ValueError("No training data available")
            
            # モデルを初期化
            model = self._create_model(model_config, contamination=contamination)
            
            # モデル訓練
            logger.info(f"Training {model_config.model_type.value} model with {X.shape[0]} samples")
            
            if model_config.model_type == ModelType.LOCAL_OUTLIER_FACTOR:
                # LOFは fit_predict を使用
                predictions = model.fit_predict(X)
                anomaly_scores = model.negative_outlier_factor_
            else:
                model.fit(X)
                predictions = model.predict(X)
                
                # 異常スコアを取得
                if hasattr(model, 'decision_function'):
                    anomaly_scores = model.decision_function(X)
                elif hasattr(model, 'score_samples'):
                    anomaly_scores = model.score_samples(X)
                else:
                    anomaly_scores = None
            
            # メトリクスを計算
            metrics = await self._calculate_anomaly_metrics(predictions, anomaly_scores)
            
            # モデルを保存
            model_id = f"{model_config.model_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            model_file_path = self.models_dir / f"{model_id}.pkl"
            
            with open(model_file_path, 'wb') as f:
                pickle.dump(model, f)
            
            # 訓練済みモデル情報を作成
            trained_model = TrainedModel(
                model_id=model_id,
                model_type=model_config.model_type,
                task_type=model_config.task_type,
                trained_at=datetime.now(timezone.utc),
                feature_names=feature_set.feature_names,
                metrics=metrics,
                hyperparameters=model_config.hyperparameters,
                model_file_path=str(model_file_path),
                metadata={
                    "training_samples": X.shape[0],
                    "features_count": X.shape[1],
                    "contamination": contamination,
                    "feature_set_metadata": feature_set.metadata
                }
            )
            
            self.trained_models[model_id] = trained_model
            logger.info(f"Successfully trained anomaly detection model: {model_id}")
            
            return trained_model
            
        except Exception as e:
            logger.error(f"Error training anomaly detection model: {e}")
            raise
    
    async def train_prediction_model(
        self,
        training_data: Dict[str, Any],
        model_config: ModelConfig
    ) -> TrainedModel:
        """
        予測モデルを訓練
        """
        try:
            if model_config.task_type not in [TaskType.REGRESSION, TaskType.CLASSIFICATION, TaskType.FORECASTING]:
                raise ValueError("Invalid task type for prediction model")
            
            X_train = training_data["X_train"]
            y_train = training_data["y_train"]
            X_test = training_data["X_test"]
            y_test = training_data["y_test"]
            
            # モデルを初期化
            model = self._create_model(model_config)
            
            # モデル訓練
            logger.info(f"Training {model_config.model_type.value} model with {X_train.shape[0]} samples")
            model.fit(X_train, y_train)
            
            # 予測
            y_pred = model.predict(X_test)
            
            # メトリクスを計算
            if model_config.task_type == TaskType.CLASSIFICATION:
                metrics = await self._calculate_classification_metrics(y_test, y_pred, model, X_train, y_train)
            else:  # REGRESSION or FORECASTING
                metrics = await self._calculate_regression_metrics(y_test, y_pred, model, X_train, y_train)
            
            # モデルを保存
            model_id = f"{model_config.model_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            model_file_path = self.models_dir / f"{model_id}.pkl"
            
            with open(model_file_path, 'wb') as f:
                pickle.dump(model, f)
            
            # 訓練済みモデル情報を作成
            trained_model = TrainedModel(
                model_id=model_id,
                model_type=model_config.model_type,
                task_type=model_config.task_type,
                trained_at=datetime.now(timezone.utc),
                feature_names=training_data["feature_names"],
                target_variable=training_data.get("target_measurement_type"),
                metrics=metrics,
                hyperparameters=model_config.hyperparameters,
                model_file_path=str(model_file_path),
                metadata={
                    "training_samples": X_train.shape[0],
                    "test_samples": X_test.shape[0],
                    "features_count": X_train.shape[1],
                    "prediction_horizon": training_data.get("prediction_horizon"),
                    "scaling_info": training_data.get("scaling_info")
                }
            )
            
            self.trained_models[model_id] = trained_model
            logger.info(f"Successfully trained prediction model: {model_id}")
            
            return trained_model
            
        except Exception as e:
            logger.error(f"Error training prediction model: {e}")
            raise
    
    async def predict(
        self,
        model_id: str,
        feature_data: np.ndarray
    ) -> PredictionResult:
        """
        モデルで予測を実行
        """
        try:
            if model_id not in self.trained_models:
                raise ValueError(f"Model {model_id} not found")
            
            trained_model = self.trained_models[model_id]
            
            # モデルをロード
            with open(trained_model.model_file_path, 'rb') as f:
                model = pickle.load(f)
            
            # 予測実行
            if trained_model.task_type == TaskType.ANOMALY_DETECTION:
                if trained_model.model_type == ModelType.LOCAL_OUTLIER_FACTOR:
                    # LOFは新しいデータに対してfit_predictが必要
                    predictions = model.fit_predict(feature_data)
                    anomaly_scores = model.negative_outlier_factor_
                else:
                    predictions = model.predict(feature_data)
                    
                    # 異常スコアを取得
                    if hasattr(model, 'decision_function'):
                        anomaly_scores = model.decision_function(feature_data)
                    elif hasattr(model, 'score_samples'):
                        anomaly_scores = model.score_samples(feature_data)
                    else:
                        anomaly_scores = None
                
                return PredictionResult(
                    predictions=predictions.tolist(),
                    anomaly_scores=anomaly_scores.tolist() if anomaly_scores is not None else None,
                    model_id=model_id,
                    predicted_at=datetime.now(timezone.utc)
                )
            
            else:
                # 分類・回帰予測
                predictions = model.predict(feature_data)
                
                # 確率を取得（分類の場合）
                probabilities = None
                if hasattr(model, 'predict_proba') and trained_model.task_type == TaskType.CLASSIFICATION:
                    probabilities = model.predict_proba(feature_data).tolist()
                
                # 特徴量重要度を取得
                feature_importance = None
                if hasattr(model, 'feature_importances_'):
                    feature_importance = {
                        name: float(importance)
                        for name, importance in zip(trained_model.feature_names, model.feature_importances_)
                    }
                
                return PredictionResult(
                    predictions=predictions.tolist(),
                    probabilities=probabilities,
                    feature_importance=feature_importance,
                    model_id=model_id,
                    predicted_at=datetime.now(timezone.utc)
                )
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            raise
    
    def _create_model(self, config: ModelConfig, **kwargs):
        """モデルを作成"""
        try:
            # デフォルトパラメータを設定
            params = config.hyperparameters.copy()
            params.update(kwargs)
            
            if config.model_type == ModelType.ISOLATION_FOREST:
                return IsolationForest(
                    contamination=params.get('contamination', 0.1),
                    n_estimators=params.get('n_estimators', 100),
                    random_state=params.get('random_state', 42)
                )
            
            elif config.model_type == ModelType.ONE_CLASS_SVM:
                return OneClassSVM(
                    nu=params.get('nu', 0.1),
                    kernel=params.get('kernel', 'rbf'),
                    gamma=params.get('gamma', 'scale')
                )
            
            elif config.model_type == ModelType.LOCAL_OUTLIER_FACTOR:
                return LocalOutlierFactor(
                    n_neighbors=params.get('n_neighbors', 20),
                    contamination=params.get('contamination', 0.1),
                    novelty=params.get('novelty', False)
                )
            
            elif config.model_type == ModelType.DBSCAN:
                return DBSCAN(
                    eps=params.get('eps', 0.5),
                    min_samples=params.get('min_samples', 5)
                )
            
            elif config.model_type == ModelType.RANDOM_FOREST_CLASSIFIER:
                return RandomForestClassifier(
                    n_estimators=params.get('n_estimators', 100),
                    max_depth=params.get('max_depth', None),
                    random_state=params.get('random_state', 42)
                )
            
            elif config.model_type == ModelType.RANDOM_FOREST_REGRESSOR:
                return RandomForestRegressor(
                    n_estimators=params.get('n_estimators', 100),
                    max_depth=params.get('max_depth', None),
                    random_state=params.get('random_state', 42)
                )
            
            elif config.model_type == ModelType.LINEAR_REGRESSION:
                return LinearRegression()
            
            elif config.model_type == ModelType.LOGISTIC_REGRESSION:
                return LogisticRegression(
                    random_state=params.get('random_state', 42),
                    max_iter=params.get('max_iter', 1000)
                )
            
            elif config.model_type == ModelType.MLP_CLASSIFIER:
                return MLPClassifier(
                    hidden_layer_sizes=params.get('hidden_layer_sizes', (100,)),
                    activation=params.get('activation', 'relu'),
                    solver=params.get('solver', 'adam'),
                    max_iter=params.get('max_iter', 200),
                    random_state=params.get('random_state', 42)
                )
            
            elif config.model_type == ModelType.MLP_REGRESSOR:
                return MLPRegressor(
                    hidden_layer_sizes=params.get('hidden_layer_sizes', (100,)),
                    activation=params.get('activation', 'relu'),
                    solver=params.get('solver', 'adam'),
                    max_iter=params.get('max_iter', 200),
                    random_state=params.get('random_state', 42)
                )
            
            else:
                raise ValueError(f"Unsupported model type: {config.model_type}")
            
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            raise
    
    async def _calculate_anomaly_metrics(
        self,
        predictions: np.ndarray,
        anomaly_scores: Optional[np.ndarray] = None
    ) -> ModelMetrics:
        """異常検知メトリクスを計算"""
        try:
            # 異常検知では正常/異常の真のラベルが不明なため、
            # 統計的な指標のみを計算
            anomaly_count = np.sum(predictions == -1)  # -1が異常
            normal_count = np.sum(predictions == 1)    # 1が正常
            
            metrics = ModelMetrics(
                task_type=TaskType.ANOMALY_DETECTION
            )
            
            # 基本統計を記録
            metrics.metadata = {
                "total_samples": len(predictions),
                "anomaly_count": int(anomaly_count),
                "normal_count": int(normal_count),
                "anomaly_ratio": float(anomaly_count / len(predictions))
            }
            
            if anomaly_scores is not None:
                metrics.metadata.update({
                    "mean_anomaly_score": float(np.mean(anomaly_scores)),
                    "std_anomaly_score": float(np.std(anomaly_scores)),
                    "min_anomaly_score": float(np.min(anomaly_scores)),
                    "max_anomaly_score": float(np.max(anomaly_scores))
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating anomaly metrics: {e}")
            raise
    
    async def _calculate_classification_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> ModelMetrics:
        """分類メトリクスを計算"""
        try:
            # クロスバリデーション
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)
            
            metrics = ModelMetrics(
                task_type=TaskType.CLASSIFICATION,
                accuracy=float(accuracy_score(y_true, y_pred)),
                precision=float(precision_score(y_true, y_pred, average='weighted', zero_division=0)),
                recall=float(recall_score(y_true, y_pred, average='weighted', zero_division=0)),
                f1_score=float(f1_score(y_true, y_pred, average='weighted', zero_division=0)),
                cross_val_scores=cv_scores.tolist(),
                confusion_matrix=confusion_matrix(y_true, y_pred).tolist(),
                classification_report=classification_report(y_true, y_pred, output_dict=True, zero_division=0)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating classification metrics: {e}")
            raise
    
    async def _calculate_regression_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> ModelMetrics:
        """回帰メトリクスを計算"""
        try:
            # クロスバリデーション
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='neg_mean_squared_error')
            
            metrics = ModelMetrics(
                task_type=TaskType.REGRESSION,
                mse=float(mean_squared_error(y_true, y_pred)),
                mae=float(mean_absolute_error(y_true, y_pred)),
                r2_score=float(r2_score(y_true, y_pred)),
                cross_val_scores=(-cv_scores).tolist()  # 負の値を正に変換
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating regression metrics: {e}")
            raise
    
    async def hyperparameter_tuning(
        self,
        feature_set: FeatureSet,
        model_config: ModelConfig,
        param_grid: Dict[str, List[Any]],
        cv: int = 5
    ) -> Dict[str, Any]:
        """
        ハイパーパラメータチューニング
        """
        try:
            X = np.array(feature_set.feature_values)
            
            # 異常検知の場合は教師なし学習なので簡単な評価
            if model_config.task_type == TaskType.ANOMALY_DETECTION:
                best_params = {}
                best_score = float('-inf')
                
                for param_combination in self._generate_param_combinations(param_grid):
                    config = ModelConfig(
                        model_type=model_config.model_type,
                        task_type=model_config.task_type,
                        hyperparameters=param_combination
                    )
                    
                    model = self._create_model(config)
                    
                    try:
                        if model_config.model_type == ModelType.LOCAL_OUTLIER_FACTOR:
                            predictions = model.fit_predict(X)
                            score = -np.mean(model.negative_outlier_factor_)
                        else:
                            model.fit(X)
                            if hasattr(model, 'score_samples'):
                                score = np.mean(model.score_samples(X))
                            else:
                                score = 0  # スコアが取得できない場合
                        
                        if score > best_score:
                            best_score = score
                            best_params = param_combination
                            
                    except Exception as e:
                        logger.warning(f"Error with parameters {param_combination}: {e}")
                        continue
                
                return {
                    "best_params": best_params,
                    "best_score": best_score,
                    "method": "manual_grid_search"
                }
            
            else:
                # 教師あり学習の場合はGridSearchCVを使用
                # ここでは簡単のため、データを半分に分けて疑似的な教師ありデータを作成
                y = X[:, 0]  # 最初の特徴量を目的変数とする
                
                model = self._create_model(model_config)
                
                grid_search = GridSearchCV(
                    model,
                    param_grid,
                    cv=cv,
                    scoring='neg_mean_squared_error' if model_config.task_type == TaskType.REGRESSION else 'accuracy'
                )
                
                grid_search.fit(X, y)
                
                return {
                    "best_params": grid_search.best_params_,
                    "best_score": grid_search.best_score_,
                    "cv_results": grid_search.cv_results_,
                    "method": "grid_search_cv"
                }
            
        except Exception as e:
            logger.error(f"Error in hyperparameter tuning: {e}")
            raise
    
    def _generate_param_combinations(self, param_grid: Dict[str, List[Any]]):
        """パラメータの組み合わせを生成"""
        import itertools
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        for combination in itertools.product(*values):
            yield dict(zip(keys, combination))
    
    async def get_model_info(self, model_id: str) -> Optional[TrainedModel]:
        """モデル情報を取得"""
        return self.trained_models.get(model_id)
    
    async def list_models(self) -> List[TrainedModel]:
        """すべてのモデルを一覧"""
        return list(self.trained_models.values())
    
    async def delete_model(self, model_id: str) -> bool:
        """モデルを削除"""
        try:
            if model_id not in self.trained_models:
                return False
            
            trained_model = self.trained_models[model_id]
            
            # ファイルを削除
            if Path(trained_model.model_file_path).exists():
                Path(trained_model.model_file_path).unlink()
            
            if trained_model.scaler_file_path and Path(trained_model.scaler_file_path).exists():
                Path(trained_model.scaler_file_path).unlink()
            
            # メモリから削除
            del self.trained_models[model_id]
            
            logger.info(f"Successfully deleted model: {model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
            return False


# グローバルインスタンス
ml_model_service = MLModelService()