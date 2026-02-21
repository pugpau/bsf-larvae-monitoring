"""ML model trainer: RandomForest classification + regression with cross-validation.

Trains two models:
- Classifier: predicts solidifier_type and suppressant_type
- Regressor: predicts solidifier_amount and suppressant_amount
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score

from src.ml.schemas import TrainingConfig
from src.ml.feature_engineering import (
    add_derived_features,
    encode_waste_type,
    impute_missing,
    prepare_features_and_targets,
)

logger = logging.getLogger(__name__)


class FormulationTrainer:
    """Train and evaluate RandomForest models for formulation prediction."""

    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self.classifier: Optional[RandomForestClassifier] = None
        self.regressor: Optional[RandomForestRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns: list = []
        self.cls_targets: list = []
        self.reg_targets: list = []
        self.metrics: Dict[str, Any] = {}

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Full training pipeline.

        Args:
            df: Flat DataFrame with analysis features + target columns.

        Returns:
            Dict of evaluation metrics.
        """
        cfg = self.config

        # 1. Feature engineering
        df = add_derived_features(df)
        df = impute_missing(df)
        df, wt_cols = encode_waste_type(df)

        # 2. Prepare features and targets
        x, y_cls, y_reg = prepare_features_and_targets(df)
        self.feature_columns = list(x.columns)

        # 3. Encode classification labels
        if y_cls is not None:
            for col in y_cls.columns:
                le = LabelEncoder()
                y_cls[col] = le.fit_transform(y_cls[col].astype(str))
                self.label_encoders[col] = le
            self.cls_targets = list(y_cls.columns)

        if y_reg is not None:
            self.reg_targets = list(y_reg.columns)

        # 4. SMOTE for class imbalance (if enabled and available)
        if cfg.use_smote and y_cls is not None and len(y_cls.columns) > 0:
            x, y_cls, y_reg = self._apply_smote(x, y_cls, y_reg)

        # 5. Train/test split
        if y_cls is not None and y_reg is not None:
            x_train, x_test, yc_train, yc_test, yr_train, yr_test = train_test_split(
                x, y_cls, y_reg,
                test_size=cfg.test_size,
                random_state=cfg.random_state,
            )
        elif y_reg is not None:
            x_train, x_test, yr_train, yr_test = train_test_split(
                x, y_reg,
                test_size=cfg.test_size,
                random_state=cfg.random_state,
            )
            yc_train = yc_test = None
        else:
            return {"error": "No target columns found"}

        # 6. Scale features
        self.scaler = StandardScaler()
        x_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(x_train),
            columns=x_train.columns,
            index=x_train.index,
        )
        x_test_scaled = pd.DataFrame(
            self.scaler.transform(x_test),
            columns=x_test.columns,
            index=x_test.index,
        )

        # 7. Train classifier
        cls_metrics = {}
        if yc_train is not None and len(self.cls_targets) > 0:
            self.classifier = RandomForestClassifier(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                min_samples_split=cfg.min_samples_split,
                random_state=cfg.random_state,
                n_jobs=-1,
            )
            # Train on first classification target (solidifier_type)
            primary_target = self.cls_targets[0]
            self.classifier.fit(x_train_scaled, yc_train[primary_target])
            y_pred = self.classifier.predict(x_test_scaled)
            cls_metrics = {
                "accuracy": round(accuracy_score(yc_test[primary_target], y_pred), 4),
                "f1_weighted": round(f1_score(yc_test[primary_target], y_pred,
                                              average="weighted", zero_division=0), 4),
            }
            # Cross-validation
            cv_scores = cross_val_score(
                self.classifier, x_train_scaled, yc_train[primary_target],
                cv=min(cfg.cv_folds, len(x_train_scaled)),
                scoring="accuracy",
            )
            cls_metrics["cv_mean"] = round(float(cv_scores.mean()), 4)
            cls_metrics["cv_std"] = round(float(cv_scores.std()), 4)

        # 8. Train regressor
        reg_metrics = {}
        if yr_train is not None and len(self.reg_targets) > 0:
            self.regressor = RandomForestRegressor(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                min_samples_split=cfg.min_samples_split,
                random_state=cfg.random_state,
                n_jobs=-1,
            )
            primary_reg = self.reg_targets[0]
            self.regressor.fit(x_train_scaled, yr_train[primary_reg])
            y_pred = self.regressor.predict(x_test_scaled)
            reg_metrics = {
                "r2": round(r2_score(yr_test[primary_reg], y_pred), 4),
                "mae": round(mean_absolute_error(yr_test[primary_reg], y_pred), 4),
            }
            cv_scores = cross_val_score(
                self.regressor, x_train_scaled, yr_train[primary_reg],
                cv=min(cfg.cv_folds, len(x_train_scaled)),
                scoring="r2",
            )
            reg_metrics["cv_mean"] = round(float(cv_scores.mean()), 4)
            reg_metrics["cv_std"] = round(float(cv_scores.std()), 4)

        self.metrics = {
            "classifier": cls_metrics,
            "regressor": reg_metrics,
            "training_samples": len(x_train),
            "test_samples": len(x_test),
            "feature_count": len(self.feature_columns),
        }
        return self.metrics

    def _apply_smote(
        self,
        x: pd.DataFrame,
        y_cls: pd.DataFrame,
        y_reg: Optional[pd.DataFrame],
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """Apply SMOTE oversampling for class imbalance."""
        try:
            from imblearn.over_sampling import SMOTE
            primary = self.cls_targets[0]
            # Check minimum class count
            min_count = y_cls[primary].value_counts().min()
            if min_count < 2:
                return x, y_cls, y_reg

            k = min(5, min_count - 1)
            smote = SMOTE(random_state=self.config.random_state, k_neighbors=k)

            if y_reg is not None:
                combined = pd.concat([y_cls, y_reg], axis=1)
                x_res, combined_res = smote.fit_resample(x, combined)
                y_cls_res = combined_res[self.cls_targets]
                y_reg_res = combined_res[self.reg_targets]
                return x_res, y_cls_res, y_reg_res

            x_res, y_cls_res = smote.fit_resample(x, y_cls)
            return x_res, y_cls_res, y_reg
        except Exception as e:
            logger.warning(f"SMOTE failed, continuing without: {e}")
            return x, y_cls, y_reg

    def predict_classification(self, features: pd.DataFrame) -> Optional[Dict[str, str]]:
        """Predict classification targets for a single sample."""
        if self.classifier is None or self.scaler is None:
            return None
        scaled = self.scaler.transform(features)
        pred = self.classifier.predict(scaled)[0]
        primary = self.cls_targets[0] if self.cls_targets else "solidifier_type"
        le = self.label_encoders.get(primary)
        label = le.inverse_transform([pred])[0] if le else str(pred)
        return {primary: label}

    def predict_regression(self, features: pd.DataFrame) -> Optional[Dict[str, float]]:
        """Predict regression targets for a single sample."""
        if self.regressor is None or self.scaler is None:
            return None
        scaled = self.scaler.transform(features)
        pred = self.regressor.predict(scaled)[0]
        primary = self.reg_targets[0] if self.reg_targets else "solidifier_amount"
        return {primary: round(float(pred), 2)}

    def save(self, directory: str, version: int) -> Dict[str, str]:
        """Save trained models, scaler, and metadata to directory.

        Returns dict of file paths.
        """
        os.makedirs(directory, exist_ok=True)
        paths: Dict[str, str] = {}

        if self.classifier:
            p = os.path.join(directory, f"classifier_v{version}.joblib")
            joblib.dump(self.classifier, p)
            paths["classifier"] = p

        if self.regressor:
            p = os.path.join(directory, f"regressor_v{version}.joblib")
            joblib.dump(self.regressor, p)
            paths["regressor"] = p

        if self.scaler:
            p = os.path.join(directory, f"scaler_v{version}.joblib")
            joblib.dump(self.scaler, p)
            paths["scaler"] = p

        # Save metadata
        meta = {
            "version": version,
            "feature_columns": self.feature_columns,
            "cls_targets": self.cls_targets,
            "reg_targets": self.reg_targets,
            "label_encoders": {k: list(v.classes_) for k, v in self.label_encoders.items()},
            "metrics": self.metrics,
        }
        meta_path = os.path.join(directory, f"metadata_v{version}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        paths["metadata"] = meta_path

        return paths

    @classmethod
    def load(cls, directory: str, version: int) -> "FormulationTrainer":
        """Load a previously trained model from directory."""
        trainer = cls()

        cls_path = os.path.join(directory, f"classifier_v{version}.joblib")
        if os.path.exists(cls_path):
            trainer.classifier = joblib.load(cls_path)

        reg_path = os.path.join(directory, f"regressor_v{version}.joblib")
        if os.path.exists(reg_path):
            trainer.regressor = joblib.load(reg_path)

        scaler_path = os.path.join(directory, f"scaler_v{version}.joblib")
        if os.path.exists(scaler_path):
            trainer.scaler = joblib.load(scaler_path)

        meta_path = os.path.join(directory, f"metadata_v{version}.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            trainer.feature_columns = meta.get("feature_columns", [])
            trainer.cls_targets = meta.get("cls_targets", [])
            trainer.reg_targets = meta.get("reg_targets", [])
            trainer.metrics = meta.get("metrics", {})

            for col, classes in meta.get("label_encoders", {}).items():
                le = LabelEncoder()
                le.classes_ = np.array(classes)
                trainer.label_encoders[col] = le

        return trainer
