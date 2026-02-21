"""Tests for ML data pipeline: extraction, flattening, validation."""

import pytest
import pandas as pd

from src.ml.data_pipeline import (
    flatten_waste_record,
    records_to_dataframe,
    validate_training_data,
)


@pytest.mark.unit
class TestFlattenWasteRecord:
    def test_flattens_analysis(self):
        record = {
            "waste_type": "汚泥（一般）",
            "source": "工場A",
            "analysis": {"pH": 7.2, "moisture": 78.5, "Pb": 0.008},
            "formulation": {"solidifierType": "普通PC", "solidifierAmount": 150},
            "elution_result": {"passed": True},
        }
        flat = flatten_waste_record(record)
        assert flat["pH"] == 7.2
        assert flat["moisture"] == 78.5
        assert flat["Pb"] == 0.008
        assert flat["solidifier_type"] == "普通PC"
        assert flat["solidifier_amount"] == 150.0
        assert flat["elution_passed"] is True

    def test_handles_missing_analysis(self):
        record = {"waste_type": "test", "source": "", "analysis": None,
                  "formulation": None, "elution_result": None}
        flat = flatten_waste_record(record)
        assert flat["pH"] is None
        assert flat["solidifier_type"] == ""
        assert flat["elution_passed"] is None

    def test_handles_empty_formulation(self):
        record = {"waste_type": "test", "source": "", "analysis": {},
                  "formulation": {}, "elution_result": {}}
        flat = flatten_waste_record(record)
        assert flat["solidifier_amount"] is None
        assert flat["elution_passed"] is None

    def test_suppressor_mapping(self):
        record = {
            "waste_type": "test", "source": "",
            "analysis": {},
            "formulation": {"suppressorType": "キレート剤A", "suppressorAmount": 3.5},
            "elution_result": {},
        }
        flat = flatten_waste_record(record)
        assert flat["suppressant_type"] == "キレート剤A"
        assert flat["suppressant_amount"] == 3.5


@pytest.mark.unit
class TestRecordsToDataframe:
    def test_creates_dataframe_from_records(self):
        records = [
            {"waste_type": "汚泥", "source": "A",
             "analysis": {"pH": 7.0}, "formulation": {"solidifierType": "PC"},
             "elution_result": {"passed": True}},
            {"waste_type": "灰", "source": "B",
             "analysis": {"pH": 8.0}, "formulation": {"solidifierType": "BFS"},
             "elution_result": {"passed": False}},
        ]
        df = records_to_dataframe(records)
        assert len(df) == 2
        assert "pH" in df.columns
        assert "solidifier_type" in df.columns

    def test_empty_records_returns_empty_df(self):
        df = records_to_dataframe([])
        assert len(df) == 0


@pytest.mark.unit
class TestValidateTrainingData:
    def test_keeps_valid_rows(self):
        df = pd.DataFrame([
            {"pH": 7.0, "moisture": 60.0, "Pb": 0.005, "As": 0.003,
             "solidifier_type": "PC", "solidifier_amount": 150.0},
        ])
        result, warnings = validate_training_data(df)
        assert len(result) == 1
        assert len(warnings) == 0

    def test_drops_rows_with_few_features(self):
        df = pd.DataFrame([
            {"pH": 7.0, "moisture": None, "Pb": None, "As": None,
             "solidifier_type": "PC", "solidifier_amount": 150.0},
        ])
        result, warnings = validate_training_data(df)
        assert len(result) == 0
        assert any("Dropped" in w for w in warnings)

    def test_drops_rows_missing_target(self):
        df = pd.DataFrame([
            {"pH": 7.0, "moisture": 60.0, "Pb": 0.005, "As": 0.003,
             "solidifier_type": "", "solidifier_amount": 150.0},
        ])
        result, warnings = validate_training_data(df)
        assert len(result) == 0

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result, warnings = validate_training_data(df)
        assert len(result) == 0
        assert any("No data" in w for w in warnings)

    def test_mixed_valid_invalid(self):
        df = pd.DataFrame([
            {"pH": 7.0, "moisture": 60.0, "Pb": 0.005, "As": 0.003,
             "solidifier_type": "PC", "solidifier_amount": 150.0},
            {"pH": 7.0, "moisture": None, "Pb": None, "As": None,
             "solidifier_type": "PC", "solidifier_amount": 150.0},
        ])
        result, warnings = validate_training_data(df)
        assert len(result) == 1
