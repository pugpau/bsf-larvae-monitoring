"""
Unit tests for the formulation recommendation engine.
"""

import math
import pytest

from src.waste.recommender import (
    _normalise,
    _weighted_distance,
    _severity_score,
    _rule_based_recommendation,
    recommend_formulation,
    ELUTION_LIMITS,
    FEATURE_RANGES,
)


# ── Normalisation ──


class TestNormalise:
    def test_within_range(self):
        assert _normalise(8.5, "pH") == pytest.approx((8.5 - 4.0) / (13.0 - 4.0))

    def test_lower_bound_clamps_to_zero(self):
        assert _normalise(0.0, "pH") == 0.0

    def test_upper_bound_clamps_to_one(self):
        assert _normalise(20.0, "pH") == 1.0

    def test_unknown_feature_uses_default(self):
        assert _normalise(0.5, "unknown") == 0.5


# ── Weighted distance ──


class TestWeightedDistance:
    def test_identical_analyses_return_zero(self, sample_waste_analysis):
        assert _weighted_distance(sample_waste_analysis, sample_waste_analysis) == pytest.approx(0.0)

    def test_different_analyses_return_positive(self, sample_waste_analysis, sample_heavy_waste_analysis):
        d = _weighted_distance(sample_waste_analysis, sample_heavy_waste_analysis)
        assert d > 0

    def test_missing_features_are_skipped(self):
        a = {"pH": 7.0}
        b = {"pH": 7.0, "Pb": 0.01}
        d = _weighted_distance(a, b)
        assert d == pytest.approx(0.0)  # only pH compared, same value

    def test_empty_dicts_return_inf(self):
        assert _weighted_distance({}, {}) == float("inf")


# ── Severity score ──


class TestSeverityScore:
    def test_clean_analysis_returns_zero(self, sample_waste_analysis):
        score = _severity_score(sample_waste_analysis)
        assert score == pytest.approx(0.0)

    def test_exceeding_analysis_returns_positive(self, sample_heavy_waste_analysis):
        score = _severity_score(sample_heavy_waste_analysis)
        assert score > 0

    def test_exactly_at_limit_returns_zero(self):
        at_limit = {k: v for k, v in ELUTION_LIMITS.items()}
        assert _severity_score(at_limit) == pytest.approx(0.0)


# ── Rule-based recommendation ──


class TestRuleBasedRecommendation:
    def test_returns_expected_keys(self, sample_waste_analysis):
        rec = _rule_based_recommendation(sample_waste_analysis, "汚泥（一般）")
        assert set(rec.keys()) == {
            "solidifierType", "solidifierAmount", "solidifierUnit",
            "suppressorType", "suppressorAmount", "suppressorUnit",
        }

    def test_high_cr6_selects_blast_furnace_cement(self):
        analysis = {"Cr6": 0.10, "moisture": 50}
        rec = _rule_based_recommendation(analysis, "焼却灰")
        assert rec["solidifierType"] == "高炉セメントB種"
        assert rec["suppressorType"] == "硫酸第一鉄"

    def test_low_cr6_selects_portland(self):
        analysis = {"Cr6": 0.01, "moisture": 50}
        rec = _rule_based_recommendation(analysis, "汚泥（一般）")
        assert rec["solidifierType"] == "普通ポルトランドセメント"

    def test_high_moisture_increases_solidifier(self):
        low_m = _rule_based_recommendation({"moisture": 50}, "汚泥（一般）")
        high_m = _rule_based_recommendation({"moisture": 90}, "汚泥（一般）")
        assert high_m["solidifierAmount"] > low_m["solidifierAmount"]


# ── Full recommendation ──


class TestRecommendFormulation:
    def test_rule_fallback_with_no_history(self, sample_waste_analysis):
        result = recommend_formulation(sample_waste_analysis, "汚泥（一般）", history=[])
        assert result["method"] == "rule"
        assert 0 < result["confidence"] <= 1.0
        assert result["recommendation"]["solidifierType"]
        assert isinstance(result["reasoning"], list)

    def test_rule_fallback_with_insufficient_history(self, sample_waste_analysis):
        history = [{"status": "formulated", "analysis": sample_waste_analysis, "formulation": {}}]
        result = recommend_formulation(sample_waste_analysis, "汚泥（一般）", history=history)
        assert result["method"] == "rule"

    def test_similarity_with_sufficient_history(self, sample_waste_analysis, formulated_history):
        result = recommend_formulation(sample_waste_analysis, "汚泥（一般）", history=formulated_history)
        assert result["method"] == "similarity"
        assert len(result["similarRecords"]) > 0
        assert result["confidence"] > 0

    def test_similarity_returns_reasonable_amounts(self, sample_waste_analysis, formulated_history):
        result = recommend_formulation(sample_waste_analysis, "汚泥（一般）", history=formulated_history)
        rec = result["recommendation"]
        assert 50 <= rec["solidifierAmount"] <= 500
        assert rec["solidifierUnit"] == "kg/t"

    def test_exceeding_analysis_lowers_rule_confidence(self, sample_heavy_waste_analysis):
        result = recommend_formulation(sample_heavy_waste_analysis, "焼却灰", history=[])
        assert result["confidence"] <= 0.3

    def test_reasoning_mentions_exceeding_items(self, sample_heavy_waste_analysis):
        result = recommend_formulation(sample_heavy_waste_analysis, "焼却灰", history=[])
        reasoning_text = " ".join(result["reasoning"])
        assert "基準超過" in reasoning_text
