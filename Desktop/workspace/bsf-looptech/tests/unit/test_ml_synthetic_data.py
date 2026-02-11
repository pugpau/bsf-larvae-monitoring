"""Tests for synthetic data generation."""

import pytest

from src.ml.synthetic_data import (
    generate_synthetic_records,
    augment_with_perturbation,
)
from src.waste.recommender import FEATURE_RANGES


@pytest.mark.unit
class TestGenerateSyntheticRecords:
    def test_generates_correct_count(self):
        records = generate_synthetic_records(n=50, seed=42)
        assert len(records) == 50

    def test_records_have_required_fields(self):
        records = generate_synthetic_records(n=5, seed=42)
        for rec in records:
            assert "waste_type" in rec
            assert "solidifier_type" in rec
            assert "solidifier_amount" in rec
            assert "elution_passed" in rec
            assert isinstance(rec["elution_passed"], bool)

    def test_analysis_values_within_ranges(self):
        records = generate_synthetic_records(n=100, seed=42)
        for rec in records:
            for feature, (lo, hi) in FEATURE_RANGES.items():
                val = rec.get(feature)
                if val is not None:
                    assert lo <= val <= hi, f"{feature}={val} out of [{lo}, {hi}]"

    def test_deterministic_with_same_seed(self):
        r1 = generate_synthetic_records(n=10, seed=123)
        r2 = generate_synthetic_records(n=10, seed=123)
        for a, b in zip(r1, r2):
            assert a["pH"] == b["pH"]
            assert a["solidifier_type"] == b["solidifier_type"]

    def test_different_seeds_produce_different_data(self):
        r1 = generate_synthetic_records(n=10, seed=1)
        r2 = generate_synthetic_records(n=10, seed=2)
        # At least some values should differ
        diffs = sum(1 for a, b in zip(r1, r2) if a["pH"] != b["pH"])
        assert diffs > 0

    def test_waste_types_are_distributed(self):
        records = generate_synthetic_records(n=200, seed=42)
        types = set(r["waste_type"] for r in records)
        assert len(types) >= 3


@pytest.mark.unit
class TestAugmentWithPerturbation:
    def test_augments_correct_count(self):
        base = generate_synthetic_records(n=5, seed=42)
        augmented = augment_with_perturbation(base, multiplier=2, seed=42)
        assert len(augmented) == 10  # 5 * 2

    def test_augmented_values_differ_from_original(self):
        base = generate_synthetic_records(n=5, seed=42)
        augmented = augment_with_perturbation(base, multiplier=1, seed=42)
        diffs = sum(1 for a, b in zip(base, augmented) if abs(a["pH"] - b["pH"]) > 0.001)
        assert diffs > 0

    def test_augmented_values_within_ranges(self):
        base = generate_synthetic_records(n=10, seed=42)
        augmented = augment_with_perturbation(base, multiplier=3, noise_std=0.2, seed=42)
        for rec in augmented:
            for feature, (lo, hi) in FEATURE_RANGES.items():
                val = rec.get(feature)
                if val is not None:
                    assert lo <= val <= hi, f"{feature}={val} out of [{lo}, {hi}]"
