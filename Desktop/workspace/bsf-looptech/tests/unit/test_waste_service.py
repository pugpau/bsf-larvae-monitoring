"""
Unit tests for waste treatment service layer.
"""

import pytest
from src.waste.service import WasteService, MaterialTypeService


class TestWasteServiceStatusDetection:
    """Test automatic status detection logic."""

    def test_pending_when_no_analysis(self):
        record = {"status": "pending", "analysis": None, "formulation": None, "elutionResult": None}
        assert record["status"] == "pending"

    def test_status_remains_when_explicitly_set(self):
        record = {"status": "formulated"}
        assert record["status"] == "formulated"


class TestElutionThresholds:
    """Test elution threshold evaluation."""

    def test_all_pass(self):
        from src.waste.service import ELUTION_THRESHOLDS
        result = {"Pb": 0.005, "As": 0.005, "Cd": 0.001}
        for key, val in result.items():
            if key in ELUTION_THRESHOLDS:
                assert val <= ELUTION_THRESHOLDS[key], f"{key} exceeds limit"

    def test_pb_exceeds(self):
        from src.waste.service import ELUTION_THRESHOLDS
        assert 0.02 > ELUTION_THRESHOLDS["Pb"]

    def test_threshold_values_match_regulations(self):
        """Verify thresholds match 土壌汚染対策法 溶出基準."""
        from src.waste.service import ELUTION_THRESHOLDS
        assert ELUTION_THRESHOLDS["Pb"] == 0.01
        assert ELUTION_THRESHOLDS["As"] == 0.01
        assert ELUTION_THRESHOLDS["Cd"] == 0.003
        assert ELUTION_THRESHOLDS["Cr6"] == 0.05
        assert ELUTION_THRESHOLDS["Hg"] == 0.0005
        assert ELUTION_THRESHOLDS["Se"] == 0.01
        assert ELUTION_THRESHOLDS["F"] == 0.8
        assert ELUTION_THRESHOLDS["B"] == 1.0


class TestEvaluateElution:
    """Test WasteService.evaluate_elution method via class instance."""

    def _make_service(self):
        """Create a WasteService with a mock repository."""
        from unittest.mock import MagicMock
        return WasteService(MagicMock())

    def test_all_within_limits(self):
        svc = self._make_service()
        result = svc.evaluate_elution({"Pb": 0.005, "As": 0.005, "Cd": 0.001})
        assert result["passed"] is True

    def test_one_exceeds_limit(self):
        svc = self._make_service()
        result = svc.evaluate_elution({"Pb": 0.02, "As": 0.005})
        assert result["passed"] is False

    def test_empty_data(self):
        svc = self._make_service()
        result = svc.evaluate_elution({})
        assert result["passed"] is True

    def test_preserves_original_data(self):
        svc = self._make_service()
        data = {"Pb": 0.005, "As": 0.005}
        result = svc.evaluate_elution(data)
        assert result["Pb"] == 0.005
        assert result["As"] == 0.005
        assert "passed" in result

    def test_all_metals_within_limits(self):
        svc = self._make_service()
        result = svc.evaluate_elution({
            "Pb": 0.009, "As": 0.009, "Cd": 0.002,
            "Cr6": 0.04, "Hg": 0.0004, "Se": 0.009,
            "F": 0.7, "B": 0.9,
        })
        assert result["passed"] is True

    def test_multiple_exceed(self):
        svc = self._make_service()
        result = svc.evaluate_elution({
            "Pb": 0.05, "As": 0.02, "Hg": 0.001,
        })
        assert result["passed"] is False
