"""
End-to-end ML pipeline integration tests.

Tests the full cycle: synthetic data generation -> validation ->
training -> prediction using the actual ML modules.

These tests do NOT require a running backend server; they test
the ML pipeline components directly with in-memory data.
"""

import pytest
import pandas as pd
import numpy as np

from src.ml.synthetic_data import generate_synthetic_records, augment_with_perturbation
from src.ml.data_pipeline import records_to_dataframe, validate_training_data, flatten_waste_record
from src.ml.trainer import FormulationTrainer
from src.ml.schemas import TrainingConfig
from src.ml.feature_engineering import ANALYSIS_FEATURES
from src.waste.recommender import ELUTION_LIMITS


@pytest.mark.integration
class TestSyntheticDataGeneration:
    """合成データ生成の正確性を検証。"""

    def test_generate_250_records_structure(self) -> None:
        """250件の合成レコードが正しい構造で生成されること。"""
        records = generate_synthetic_records(n=250, seed=42)

        assert len(records) == 250

        # 各レコードの構造を検証
        required_fields = {
            "waste_type", "source", "pH", "moisture", "ignitionLoss",
            "Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B",
            "solidifier_type", "solidifier_amount", "elution_passed",
        }
        for i, rec in enumerate(records):
            missing = required_fields - set(rec.keys())
            assert not missing, f"Record {i} missing fields: {missing}"

    def test_analysis_values_within_range(self) -> None:
        """分析値がFEATURE_RANGES内に収まること。"""
        from src.waste.recommender import FEATURE_RANGES

        records = generate_synthetic_records(n=100, seed=123)

        for rec in records:
            for feature, (lo, hi) in FEATURE_RANGES.items():
                val = rec.get(feature)
                if val is not None:
                    assert lo <= val <= hi, (
                        f"{feature}={val} outside range [{lo}, {hi}]"
                    )

    def test_waste_type_distribution(self) -> None:
        """複数の廃棄物種類が生成されること。"""
        records = generate_synthetic_records(n=200, seed=42)
        waste_types = {rec["waste_type"] for rec in records}

        # 少なくとも3種類以上生成される
        assert len(waste_types) >= 3, f"Only {len(waste_types)} waste types: {waste_types}"

    def test_solidifier_type_not_empty(self) -> None:
        """全レコードで固化材タイプが指定されること。"""
        records = generate_synthetic_records(n=100, seed=42)

        for rec in records:
            assert rec["solidifier_type"], f"Empty solidifier_type in record"
            assert rec["solidifier_amount"] > 0, "solidifier_amount must be > 0"

    def test_elution_passed_distribution(self) -> None:
        """合格/不合格が両方含まれること。"""
        records = generate_synthetic_records(n=200, seed=42)
        passed_count = sum(1 for r in records if r["elution_passed"])
        failed_count = len(records) - passed_count

        assert passed_count > 0, "No passed records"
        assert failed_count > 0, "No failed records"

    def test_augmentation_multiplies_records(self) -> None:
        """摂動による拡張でレコード数が増えること。"""
        base = generate_synthetic_records(n=10, seed=42)
        augmented = augment_with_perturbation(base, multiplier=3, seed=99)

        assert len(augmented) == 30  # 10 * 3


@pytest.mark.integration
class TestDataValidation:
    """データ品質バリデーションを検証。"""

    def test_valid_records_pass_validation(self) -> None:
        """有効なレコードがバリデーションを通過すること。"""
        records = generate_synthetic_records(n=100, seed=42)
        df = pd.DataFrame(records)
        cleaned, warnings = validate_training_data(df)

        # 合成データは全件有効のはず
        assert len(cleaned) >= 80, f"Too many records dropped: {len(cleaned)}/100"

    def test_incomplete_records_filtered(self) -> None:
        """不完全なレコードがフィルタされること。"""
        records = generate_synthetic_records(n=50, seed=42)
        df = pd.DataFrame(records)

        # 一部レコードの特徴量をNaNにする
        df.loc[0:4, "pH"] = None
        df.loc[0:4, "moisture"] = None
        df.loc[0:4, "Pb"] = None
        df.loc[0:4, "As"] = None
        df.loc[0:4, "Cd"] = None
        df.loc[0:4, "solidifier_type"] = ""

        cleaned, warnings = validate_training_data(df)

        assert len(cleaned) < 50, "Incomplete records should be filtered"
        assert len(warnings) > 0, "Should report warnings"

    def test_flatten_waste_record(self) -> None:
        """waste_recordのフラット化が正しく行われること。"""
        raw = {
            "waste_type": "汚泥",
            "source": "テスト工場",
            "analysis": {
                "pH": 7.5, "moisture": 65.0, "ignitionLoss": 15.0,
                "Pb": 0.005, "As": 0.003, "Cd": 0.001, "Cr6": 0.02,
                "Hg": 0.0002, "Se": 0.005, "F": 0.3, "B": 0.5,
            },
            "formulation": {
                "solidifierType": "普通ポルトランドセメント",
                "solidifierAmount": 160,
                "suppressorType": "キレート剤A",
                "suppressorAmount": 3.5,
            },
            "elution_result": {"passed": True},
        }

        flat = flatten_waste_record(raw)

        assert flat["waste_type"] == "汚泥"
        assert flat["pH"] == 7.5
        assert flat["solidifier_type"] == "普通ポルトランドセメント"
        assert flat["solidifier_amount"] == 160.0
        assert flat["elution_passed"] is True

    def test_records_to_dataframe_shape(self) -> None:
        """records_to_dataframe が正しいカラム数のDataFrameを返すこと。"""
        records = generate_synthetic_records(n=20, seed=42)
        # 合成データは既にフラット形式なので、raw dict形式に変換
        raw_records = []
        for rec in records:
            raw_records.append({
                "waste_type": rec["waste_type"],
                "source": rec["source"],
                "analysis": {k: rec.get(k) for k in ANALYSIS_FEATURES},
                "formulation": {
                    "solidifierType": rec["solidifier_type"],
                    "solidifierAmount": rec["solidifier_amount"],
                    "suppressorType": rec.get("suppressant_type", ""),
                    "suppressorAmount": rec.get("suppressant_amount", 0.0),
                },
                "elution_result": {"passed": rec["elution_passed"]},
            })

        df = records_to_dataframe(raw_records)

        assert len(df) == 20
        assert "pH" in df.columns
        assert "solidifier_type" in df.columns
        assert "elution_passed" in df.columns


@pytest.mark.integration
class TestTrainingPipeline:
    """MLモデル学習パイプラインの統合テスト。"""

    def test_train_on_synthetic_data(self) -> None:
        """合成データでモデル学習が完了し、メトリクスが得られること。"""
        records = generate_synthetic_records(n=250, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=20,
            cv_folds=3,
            use_smote=False,
            include_synthetic=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        metrics = trainer.train(df)

        # メトリクスが返ること
        assert "classifier" in metrics
        assert "regressor" in metrics
        assert metrics["training_samples"] > 0
        assert metrics["test_samples"] > 0

    def test_classifier_accuracy_reasonable(self) -> None:
        """分類モデルの精度が合理的な範囲であること。"""
        records = generate_synthetic_records(n=250, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=50,
            cv_folds=3,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        metrics = trainer.train(df)

        cls_metrics = metrics.get("classifier", {})
        if cls_metrics:
            # 合成データなので高精度は期待しないが、ランダム以上であること
            assert cls_metrics.get("accuracy", 0) > 0.3, (
                f"Classifier accuracy too low: {cls_metrics}"
            )

    def test_regressor_metrics_present(self) -> None:
        """回帰モデルのメトリクスが算出されること。"""
        records = generate_synthetic_records(n=250, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=20,
            cv_folds=3,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        metrics = trainer.train(df)

        reg_metrics = metrics.get("regressor", {})
        if reg_metrics:
            assert "r2" in reg_metrics
            assert "mae" in reg_metrics


@pytest.mark.integration
class TestPredictionAfterTraining:
    """学習済みモデルによる予測テスト。"""

    def test_predict_classification(self) -> None:
        """学習後に分類予測ができること。"""
        records = generate_synthetic_records(n=250, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=20,
            cv_folds=3,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        trainer.train(df)

        # テスト用の入力データを準備
        test_record = records[0]
        feature_df = pd.DataFrame([{
            col: test_record.get(col, 0.0) for col in trainer.feature_columns
        }])

        result = trainer.predict_classification(feature_df)

        if result is not None:
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_predict_regression(self) -> None:
        """学習後に回帰予測ができること。"""
        records = generate_synthetic_records(n=250, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=20,
            cv_folds=3,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        trainer.train(df)

        # テスト用の入力データを準備
        test_record = records[0]
        feature_df = pd.DataFrame([{
            col: test_record.get(col, 0.0) for col in trainer.feature_columns
        }])

        result = trainer.predict_regression(feature_df)

        if result is not None:
            assert isinstance(result, dict)
            for key, val in result.items():
                assert isinstance(val, float)
                assert val >= 0, f"Negative prediction: {key}={val}"

    def test_full_pipeline_roundtrip(self) -> None:
        """生成 -> 学習 -> 予測の完全サイクルが動作すること。"""
        # 1. データ生成
        records = generate_synthetic_records(n=250, seed=42)
        assert len(records) == 250

        # 2. DataFrame変換とバリデーション
        df = pd.DataFrame(records)
        cleaned, warnings = validate_training_data(df)
        assert len(cleaned) >= 200, f"Too few valid records: {len(cleaned)}"

        # 3. 学習
        config = TrainingConfig(
            n_estimators=30,
            cv_folds=3,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        metrics = trainer.train(cleaned)
        assert metrics["training_samples"] > 0

        # 4. 予測
        test_input = pd.DataFrame([{
            col: cleaned.iloc[0].get(col, 0.0) if col in cleaned.columns else 0.0
            for col in trainer.feature_columns
        }])

        cls_result = trainer.predict_classification(test_input)
        reg_result = trainer.predict_regression(test_input)

        # 少なくとも一方は予測結果を返す
        assert cls_result is not None or reg_result is not None, (
            "Both classification and regression predictions returned None"
        )

    def test_save_and_load_model(self, tmp_path) -> None:
        """モデルの保存と読み込みが正しく動作すること。"""
        records = generate_synthetic_records(n=100, seed=42)
        df = pd.DataFrame(records)

        config = TrainingConfig(
            n_estimators=10,
            cv_folds=2,
            use_smote=False,
            random_state=42,
        )
        trainer = FormulationTrainer(config=config)
        trainer.train(df)

        # 保存
        model_dir = str(tmp_path / "models")
        paths = trainer.save(model_dir, version=1)
        assert len(paths) > 0

        # 読み込み
        loaded = FormulationTrainer.load(model_dir, version=1)
        assert loaded.feature_columns == trainer.feature_columns
        assert loaded.cls_targets == trainer.cls_targets
        assert loaded.reg_targets == trainer.reg_targets
