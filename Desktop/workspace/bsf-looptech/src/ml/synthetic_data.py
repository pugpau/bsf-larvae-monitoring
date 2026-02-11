"""Synthetic data generation for ML training bootstrap.

Generates realistic waste treatment records using the existing rule-based
recommender as a ground-truth generator, with added noise for variety.
"""

from typing import Any, Dict, List

import numpy as np

from src.waste.recommender import (
    ELUTION_LIMITS,
    FEATURE_RANGES,
    _rule_based_recommendation,
)

# Waste type distribution for synthetic data
WASTE_TYPES = ["汚泥（一般）", "焼却灰", "飛灰", "建設汚泥", "浄水汚泥"]
WASTE_TYPE_WEIGHTS = [0.4, 0.25, 0.15, 0.1, 0.1]


def generate_synthetic_records(n: int = 200, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate n synthetic waste treatment records.

    Each record contains:
    - Random analysis within FEATURE_RANGES (biased toward realistic values)
    - Rule-based formulation via recommender
    - Simulated elution result with noise

    Args:
        n: Number of records to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of dicts in the same format as flatten_waste_record output.
    """
    rng = np.random.default_rng(seed)
    records: List[Dict[str, Any]] = []

    for i in range(n):
        waste_type = rng.choice(WASTE_TYPES, p=WASTE_TYPE_WEIGHTS)
        analysis = _generate_analysis(rng, waste_type)
        formulation = _rule_based_recommendation(analysis, waste_type)
        elution_passed = _simulate_elution(rng, analysis, formulation)

        records.append({
            "waste_type": waste_type,
            "source": f"synthetic_{i}",
            "pH": analysis.get("pH"),
            "moisture": analysis.get("moisture"),
            "ignitionLoss": analysis.get("ignitionLoss"),
            "Pb": analysis.get("Pb"),
            "As": analysis.get("As"),
            "Cd": analysis.get("Cd"),
            "Cr6": analysis.get("Cr6"),
            "Hg": analysis.get("Hg"),
            "Se": analysis.get("Se"),
            "F": analysis.get("F"),
            "B": analysis.get("B"),
            "solidifier_type": formulation["solidifierType"],
            "solidifier_amount": formulation["solidifierAmount"],
            "suppressant_type": formulation.get("suppressorType", ""),
            "suppressant_amount": formulation.get("suppressorAmount", 0.0),
            "elution_passed": elution_passed,
        })

    return records


def _generate_analysis(rng: np.random.Generator, waste_type: str) -> Dict[str, float]:
    """Generate a realistic analysis dict for the given waste type."""
    analysis: Dict[str, float] = {}

    # Base ranges with waste-type specific biases
    biases = _get_waste_type_biases(waste_type)

    for feature, (lo, hi) in FEATURE_RANGES.items():
        bias = biases.get(feature, 0.5)
        # Beta distribution centered around bias point
        alpha = max(1.0, bias * 4)
        beta_param = max(1.0, (1.0 - bias) * 4)
        val = rng.beta(alpha, beta_param) * (hi - lo) + lo
        analysis[feature] = round(float(val), 6)

    return analysis


def _get_waste_type_biases(waste_type: str) -> Dict[str, float]:
    """Get feature distribution biases by waste type (0=low, 1=high within range)."""
    base = {
        "pH": 0.5, "moisture": 0.6, "ignitionLoss": 0.3,
        "Pb": 0.15, "As": 0.1, "Cd": 0.1, "Cr6": 0.15,
        "Hg": 0.1, "Se": 0.1, "F": 0.15, "B": 0.1,
    }
    if waste_type == "焼却灰":
        base.update({"moisture": 0.2, "ignitionLoss": 0.1,
                      "Pb": 0.3, "Cr6": 0.25, "pH": 0.7})
    elif waste_type == "飛灰":
        base.update({"moisture": 0.15, "Pb": 0.4, "Cd": 0.3,
                      "Cr6": 0.3, "Hg": 0.2, "pH": 0.8})
    elif waste_type == "建設汚泥":
        base.update({"moisture": 0.7, "ignitionLoss": 0.2, "pH": 0.45})
    elif waste_type == "浄水汚泥":
        base.update({"moisture": 0.8, "As": 0.2, "F": 0.25})
    return base


def _simulate_elution(
    rng: np.random.Generator,
    analysis: Dict[str, float],
    formulation: Dict[str, Any],
) -> bool:
    """Simulate elution test outcome based on analysis and formulation quality.

    Higher solidifier amount → better treatment → higher pass probability.
    Higher metal concentration → harder to treat → lower pass probability.
    """
    solidifier_amt = formulation.get("solidifierAmount", 150)
    # Treatment effectiveness: more solidifier = better
    effectiveness = min(1.0, solidifier_amt / 200.0)

    # Metal severity reduces pass probability
    severity = 0.0
    for metal, limit in ELUTION_LIMITS.items():
        val = analysis.get(metal, 0.0)
        if limit > 0 and val > limit:
            severity += (val / limit - 1.0)

    pass_prob = max(0.05, min(0.98, effectiveness * 0.8 - severity * 0.15 + 0.15))
    return bool(rng.random() < pass_prob)


def augment_with_perturbation(
    records: List[Dict[str, Any]],
    multiplier: int = 3,
    noise_std: float = 0.1,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Create perturbed copies of existing records for data augmentation.

    For each record, creates `multiplier` variants with Gaussian noise
    added to numeric features. Non-numeric fields are preserved.

    Args:
        records: Source records (flat dict format).
        multiplier: Number of copies per record.
        noise_std: Standard deviation of noise relative to feature range.
        seed: Random seed.

    Returns:
        List of augmented records (original records NOT included).
    """
    rng = np.random.default_rng(seed)
    numeric_keys = set(FEATURE_RANGES.keys()) | {"solidifier_amount", "suppressant_amount"}
    augmented: List[Dict[str, Any]] = []

    for record in records:
        for _ in range(multiplier):
            new_rec = dict(record)
            for key in numeric_keys:
                val = record.get(key)
                if val is None or not isinstance(val, (int, float)):
                    continue
                lo, hi = FEATURE_RANGES.get(key, (0.0, max(1.0, float(val) * 2)))
                noise = rng.normal(0, noise_std * (hi - lo))
                new_val = max(lo, min(hi, val + noise))
                new_rec[key] = round(float(new_val), 6)
            augmented.append(new_rec)

    return augmented
