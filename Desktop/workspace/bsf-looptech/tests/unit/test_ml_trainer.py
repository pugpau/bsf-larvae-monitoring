"""Tests for ML model trainer: training, evaluation, save/load."""

import os
import pytest
import pandas as pd

from src.ml.schemas import TrainingConfig
from src.ml.synthetic_data import generate_synthetic_records
from src.ml.trainer import FormulationTrainer


@pytest.fixture
def training_df():
    """DataFrame of 100 synthetic records for training tests."""
    records = generate_synthetic_records(n=100, seed=42)
    return pd.DataFrame(records)


@pytest.fixture
def small_training_df():
    """Small DataFrame for quick tests."""
    records = generate_synthetic_records(n=30, seed=42)
    return pd.DataFrame(records)


@pytest.mark.unit
class TestFormulationTrainer:
    def test_train_returns_metrics(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, cv_folds=3, use_smote=False, random_state=42,
        ))
        metrics = trainer.train(training_df)
        assert "classifier" in metrics
        assert "regressor" in metrics
        assert "training_samples" in metrics

    def test_classifier_accuracy_above_threshold(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=50, use_smote=False, random_state=42,
        ))
        metrics = trainer.train(training_df)
        # Synthetic data from rules should be highly predictable
        assert metrics["classifier"]["accuracy"] >= 0.5

    def test_regressor_r2_above_threshold(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=50, use_smote=False, random_state=42,
        ))
        metrics = trainer.train(training_df)
        assert metrics["regressor"]["r2"] >= 0.0  # At least better than mean

    def test_cross_validation_included(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, cv_folds=3, use_smote=False, random_state=42,
        ))
        metrics = trainer.train(training_df)
        assert "cv_mean" in metrics["classifier"]
        assert "cv_std" in metrics["classifier"]

    def test_predict_classification(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, use_smote=False, random_state=42,
        ))
        trainer.train(training_df)
        # Build a single sample
        sample = training_df.iloc[[0]].drop(
            columns=["solidifier_type", "suppressant_type",
                     "solidifier_amount", "suppressant_amount",
                     "elution_passed", "waste_type", "source"],
            errors="ignore",
        ).select_dtypes(include=["number"])
        # Align features
        for col in trainer.feature_columns:
            if col not in sample.columns:
                sample[col] = 0
        sample = sample[trainer.feature_columns]

        result = trainer.predict_classification(sample)
        assert result is not None
        assert "solidifier_type" in result

    def test_predict_regression(self, training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, use_smote=False, random_state=42,
        ))
        trainer.train(training_df)
        sample = training_df.iloc[[0]].drop(
            columns=["solidifier_type", "suppressant_type",
                     "solidifier_amount", "suppressant_amount",
                     "elution_passed", "waste_type", "source"],
            errors="ignore",
        ).select_dtypes(include=["number"])
        for col in trainer.feature_columns:
            if col not in sample.columns:
                sample[col] = 0
        sample = sample[trainer.feature_columns]

        result = trainer.predict_regression(sample)
        assert result is not None
        assert "solidifier_amount" in result
        assert result["solidifier_amount"] > 0

    def test_predict_without_training_returns_none(self):
        trainer = FormulationTrainer()
        sample = pd.DataFrame({"pH": [7.0]})
        assert trainer.predict_classification(sample) is None
        assert trainer.predict_regression(sample) is None


@pytest.mark.unit
class TestTrainerSaveLoad:
    def test_save_creates_files(self, training_df, tmp_path):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, use_smote=False, random_state=42,
        ))
        trainer.train(training_df)
        paths = trainer.save(str(tmp_path), version=1)
        assert os.path.exists(paths["classifier"])
        assert os.path.exists(paths["regressor"])
        assert os.path.exists(paths["scaler"])
        assert os.path.exists(paths["metadata"])

    def test_load_restores_predictions(self, training_df, tmp_path):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, use_smote=False, random_state=42,
        ))
        trainer.train(training_df)
        trainer.save(str(tmp_path), version=1)

        loaded = FormulationTrainer.load(str(tmp_path), version=1)
        assert loaded.classifier is not None
        assert loaded.regressor is not None
        assert loaded.feature_columns == trainer.feature_columns

    def test_loaded_model_produces_same_predictions(self, training_df, tmp_path):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, use_smote=False, random_state=42,
        ))
        trainer.train(training_df)
        trainer.save(str(tmp_path), version=1)

        loaded = FormulationTrainer.load(str(tmp_path), version=1)

        # Build sample
        sample = training_df.iloc[[0]].drop(
            columns=["solidifier_type", "suppressant_type",
                     "solidifier_amount", "suppressant_amount",
                     "elution_passed", "waste_type", "source"],
            errors="ignore",
        ).select_dtypes(include=["number"])
        for col in trainer.feature_columns:
            if col not in sample.columns:
                sample[col] = 0
        sample = sample[trainer.feature_columns]

        orig = trainer.predict_regression(sample)
        restored = loaded.predict_regression(sample)
        assert orig["solidifier_amount"] == pytest.approx(restored["solidifier_amount"])


@pytest.mark.unit
class TestSmote:
    def test_smote_does_not_crash(self, small_training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, cv_folds=2, use_smote=True, random_state=42,
        ))
        metrics = trainer.train(small_training_df)
        assert "classifier" in metrics

    def test_smote_disabled(self, small_training_df):
        trainer = FormulationTrainer(TrainingConfig(
            n_estimators=10, cv_folds=2, use_smote=False, random_state=42,
        ))
        metrics = trainer.train(small_training_df)
        assert "classifier" in metrics
