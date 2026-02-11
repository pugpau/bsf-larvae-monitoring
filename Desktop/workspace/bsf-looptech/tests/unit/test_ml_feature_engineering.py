"""Tests for ML feature engineering module."""

import pytest
import pandas as pd
import numpy as np

from src.ml.feature_engineering import (
    severity_score,
    metal_count_exceeded,
    max_exceedance_ratio,
    add_derived_features,
    encode_waste_type,
    impute_missing,
    prepare_features_and_targets,
)


@pytest.mark.unit
class TestSeverityScore:
    def test_clean_sample_returns_zero(self):
        row = pd.Series({"Pb": 0.005, "As": 0.005, "Cd": 0.001, "Cr6": 0.01})
        assert severity_score(row) == pytest.approx(0.0)

    def test_exceeding_sample_returns_positive(self):
        row = pd.Series({"Pb": 0.05, "As": 0.005})  # Pb = 5x limit
        assert severity_score(row) > 0

    def test_exactly_at_limit_returns_zero(self):
        row = pd.Series({"Pb": 0.01, "As": 0.01, "Cd": 0.003})
        assert severity_score(row) == pytest.approx(0.0)

    def test_nan_values_are_skipped(self):
        row = pd.Series({"Pb": float("nan"), "As": 0.005})
        assert severity_score(row) == pytest.approx(0.0)


@pytest.mark.unit
class TestMetalCountExceeded:
    def test_clean_returns_zero(self):
        row = pd.Series({"Pb": 0.005, "As": 0.005})
        assert metal_count_exceeded(row) == 0

    def test_two_exceeded(self):
        row = pd.Series({"Pb": 0.05, "As": 0.05, "Cd": 0.001})
        assert metal_count_exceeded(row) == 2

    def test_all_exceeded(self):
        row = pd.Series({"Pb": 1.0, "As": 1.0, "Cd": 1.0, "Cr6": 1.0,
                         "Hg": 1.0, "Se": 1.0, "F": 10.0, "B": 10.0})
        assert metal_count_exceeded(row) == 8


@pytest.mark.unit
class TestMaxExceedanceRatio:
    def test_clean_returns_below_one(self):
        row = pd.Series({"Pb": 0.005})  # 0.005 / 0.01 = 0.5
        assert max_exceedance_ratio(row) == pytest.approx(0.5)

    def test_exceeded_returns_above_one(self):
        row = pd.Series({"Pb": 0.05})  # 0.05 / 0.01 = 5.0
        assert max_exceedance_ratio(row) == pytest.approx(5.0)


@pytest.mark.unit
class TestAddDerivedFeatures:
    def test_adds_expected_columns(self):
        df = pd.DataFrame([{"pH": 7.0, "moisture": 70.0, "Pb": 0.005}])
        result = add_derived_features(df)
        assert "severity_score" in result.columns
        assert "metal_count_exceeded" in result.columns
        assert "max_exceedance_ratio" in result.columns
        assert "ph_deviation" in result.columns
        assert "moisture_high" in result.columns

    def test_ph_deviation_from_neutral(self):
        df = pd.DataFrame([{"pH": 9.5}])
        result = add_derived_features(df)
        assert result["ph_deviation"].iloc[0] == pytest.approx(2.5)

    def test_moisture_high_flag(self):
        df = pd.DataFrame([{"moisture": 70.0}, {"moisture": 40.0}])
        result = add_derived_features(df)
        assert result["moisture_high"].iloc[0] == 1
        assert result["moisture_high"].iloc[1] == 0

    def test_preserves_original_columns(self):
        df = pd.DataFrame([{"pH": 7.0, "Pb": 0.005}])
        result = add_derived_features(df)
        assert "pH" in result.columns
        assert "Pb" in result.columns


@pytest.mark.unit
class TestEncodeWasteType:
    def test_one_hot_encoding(self):
        df = pd.DataFrame([{"waste_type": "汚泥", "pH": 7.0},
                          {"waste_type": "焼却灰", "pH": 8.0}])
        result, new_cols = encode_waste_type(df)
        assert "waste_type" not in result.columns
        assert len(new_cols) == 2
        assert "pH" in result.columns

    def test_no_waste_type_column(self):
        df = pd.DataFrame([{"pH": 7.0}])
        result, new_cols = encode_waste_type(df)
        assert len(new_cols) == 0
        assert len(result) == 1


@pytest.mark.unit
class TestImputeMissing:
    def test_fills_nan_with_median(self):
        df = pd.DataFrame({"pH": [7.0, None, 8.0]})
        result = impute_missing(df, columns=["pH"])
        assert result["pH"].iloc[1] == pytest.approx(7.5)

    def test_remaining_nan_filled_with_zero(self):
        df = pd.DataFrame({"pH": [None, None, None]})
        result = impute_missing(df, columns=["pH"])
        assert (result["pH"] == 0).all()


@pytest.mark.unit
class TestPrepareFeatures:
    def test_splits_features_and_targets(self):
        df = pd.DataFrame({
            "pH": [7.0], "moisture": [60.0],
            "solidifier_type": ["cement"], "solidifier_amount": [150.0],
            "suppressant_type": ["chelate"], "suppressant_amount": [3.0],
            "elution_passed": [True],
        })
        x, y_cls, y_reg = prepare_features_and_targets(df)
        assert "pH" in x.columns
        assert "solidifier_type" not in x.columns
        assert "solidifier_amount" not in x.columns
        assert y_cls is not None
        assert "solidifier_type" in y_cls.columns
        assert y_reg is not None
        assert "solidifier_amount" in y_reg.columns

    def test_no_targets_returns_none(self):
        df = pd.DataFrame({"pH": [7.0], "moisture": [60.0]})
        x, y_cls, y_reg = prepare_features_and_targets(df)
        assert "pH" in x.columns
        assert y_cls is None
        assert y_reg is None
