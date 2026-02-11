"""
Formulation recommendation engine for waste treatment.

Strategy:
1. Similarity-based: find past records with similar waste analysis profiles
2. Rule-based adjustments: scale amounts based on heavy metal concentrations
3. Confidence scoring: based on similarity distance and outcome data

When sufficient data accumulates (>50 formulated records), this can be
upgraded to a scikit-learn regression model with minimal API changes.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Regulatory thresholds (mg/L) — 土壌汚染対策法 溶出基準
ELUTION_LIMITS = {
    "Pb": 0.01, "As": 0.01, "Cd": 0.003, "Cr6": 0.05,
    "Hg": 0.0005, "Se": 0.01, "F": 0.8, "B": 1.0,
}

# Feature weights for similarity calculation (higher = more influential)
FEATURE_WEIGHTS = {
    "pH": 1.0, "moisture": 0.8, "ignitionLoss": 0.6,
    "Pb": 2.0, "As": 2.0, "Cd": 2.5, "Cr6": 2.0,
    "Hg": 2.5, "Se": 1.5, "F": 1.5, "B": 1.0,
}

# Typical ranges for normalisation (min, max observed)
FEATURE_RANGES = {
    "pH": (4.0, 13.0), "moisture": (10.0, 95.0), "ignitionLoss": (2.0, 60.0),
    "Pb": (0.0, 0.2), "As": (0.0, 0.05), "Cd": (0.0, 0.01),
    "Cr6": (0.0, 0.3), "Hg": (0.0, 0.002), "Se": (0.0, 0.03),
    "F": (0.0, 2.0), "B": (0.0, 1.5),
}

# Rule-based solidifier guidelines
SOLIDIFIER_RULES = {
    "汚泥（一般）": {"base": 150, "moisture_factor": 0.5, "metal_factor": 50},
    "焼却灰": {"base": 180, "moisture_factor": 0.2, "metal_factor": 60},
}

DEFAULT_SOLIDIFIER_RULE = {"base": 160, "moisture_factor": 0.4, "metal_factor": 55}


def _normalise(value: float, feature: str) -> float:
    """Normalise a feature value to 0–1 range."""
    lo, hi = FEATURE_RANGES.get(feature, (0.0, 1.0))
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _weighted_distance(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Compute weighted Euclidean distance between two analysis dicts."""
    total = 0.0
    weight_sum = 0.0
    for feat, weight in FEATURE_WEIGHTS.items():
        va = a.get(feat)
        vb = b.get(feat)
        if va is None or vb is None:
            continue
        na = _normalise(float(va), feat)
        nb = _normalise(float(vb), feat)
        total += weight * (na - nb) ** 2
        weight_sum += weight
    if weight_sum == 0:
        return float("inf")
    return math.sqrt(total / weight_sum)


def _severity_score(analysis: Dict[str, Any]) -> float:
    """How much the analysis exceeds regulatory limits (0 = clean, higher = worse)."""
    score = 0.0
    for metal, limit in ELUTION_LIMITS.items():
        val = analysis.get(metal)
        if val is not None and limit > 0:
            ratio = float(val) / limit
            if ratio > 1.0:
                score += (ratio - 1.0) * FEATURE_WEIGHTS.get(metal, 1.0)
    return score


def _rule_based_recommendation(
    analysis: Dict[str, Any], waste_type: str
) -> Dict[str, Any]:
    """Generate a rule-based formulation when no similar records exist."""
    rules = SOLIDIFIER_RULES.get(waste_type, DEFAULT_SOLIDIFIER_RULE)
    moisture = float(analysis.get("moisture", 50))
    severity = _severity_score(analysis)

    solidifier_amount = (
        rules["base"]
        + max(0, moisture - 60) * rules["moisture_factor"]
        + severity * rules["metal_factor"]
    )

    # Determine solidifier type based on Cr6 levels
    cr6 = float(analysis.get("Cr6", 0))
    if cr6 > 0.05:
        solidifier_type = "高炉セメントB種"
    else:
        solidifier_type = "普通ポルトランドセメント"

    # Determine suppressor need
    suppressor_type = ""
    suppressor_amount = 0.0
    if cr6 > 0.04:
        suppressor_type = "硫酸第一鉄"
        suppressor_amount = round(2.0 + severity * 3.0, 1)
    elif severity > 0.5:
        suppressor_type = "キレート剤A"
        suppressor_amount = round(2.0 + severity * 2.0, 1)

    return {
        "solidifierType": solidifier_type,
        "solidifierAmount": round(solidifier_amount),
        "solidifierUnit": "kg/t",
        "suppressorType": suppressor_type,
        "suppressorAmount": suppressor_amount,
        "suppressorUnit": "kg/t",
    }


def recommend_formulation(
    analysis: Dict[str, Any],
    waste_type: str,
    history: List[Dict[str, Any]],
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Recommend a formulation for the given waste analysis.

    Args:
        analysis: Current waste analysis data {pH, moisture, Pb, As, ...}
        waste_type: Waste type string (e.g. "汚泥（一般）")
        history: List of past waste records with formulation and elutionResult
        top_k: Number of similar records to consider

    Returns:
        {
            recommendation: {solidifierType, solidifierAmount, ...},
            confidence: float 0-1,
            method: "similarity" | "rule",
            reasoning: [str],
            similar_records: [{id, source, date, distance, formulation, passed}]
        }
    """
    # Filter history to formulated records with successful elution results
    successful = [
        r for r in history
        if r.get("status") == "formulated"
        and r.get("formulation")
        and r.get("analysis")
        and isinstance(r.get("analysis"), dict)
        and any(v is not None for k, v in r["analysis"].items() if k in FEATURE_WEIGHTS)
    ]

    reasoning = []

    # Severity analysis
    severity = _severity_score(analysis)
    exceeding = []
    for metal, limit in ELUTION_LIMITS.items():
        val = analysis.get(metal)
        if val is not None and float(val) > limit:
            exceeding.append(f"{metal}: {val} mg/L (基準値 {limit} の {float(val)/limit:.1f}倍)")

    if exceeding:
        reasoning.append(f"基準超過項目: {', '.join(exceeding)}")
    else:
        reasoning.append("全項目基準値内")

    # If we have enough similar records, use similarity-based approach
    if len(successful) >= 3:
        distances = []
        for rec in successful:
            dist = _weighted_distance(analysis, rec["analysis"])
            distances.append((dist, rec))

        distances.sort(key=lambda x: x[0])
        nearest = distances[:top_k]

        # Weighted average of formulations from similar records
        total_weight = 0.0
        avg_solidifier_amount = 0.0
        avg_suppressor_amount = 0.0
        solidifier_counts = {}
        suppressor_counts = {}

        similar_records = []
        for dist, rec in nearest:
            w = 1.0 / (dist + 0.01)  # Inverse distance weighting
            total_weight += w
            form = rec["formulation"]

            avg_solidifier_amount += w * float(form.get("solidifierAmount", 0))
            avg_suppressor_amount += w * float(form.get("suppressorAmount", 0))

            st = form.get("solidifierType", "")
            if st:
                solidifier_counts[st] = solidifier_counts.get(st, 0) + w

            su = form.get("suppressorType", "")
            if su:
                suppressor_counts[su] = suppressor_counts.get(su, 0) + w

            passed = rec.get("elutionResult", {}).get("passed") if rec.get("elutionResult") else None
            similar_records.append({
                "id": rec.get("id"),
                "source": rec.get("source"),
                "deliveryDate": rec.get("deliveryDate"),
                "distance": round(dist, 4),
                "formulation": form,
                "passed": passed,
            })

        if total_weight > 0:
            avg_solidifier_amount /= total_weight
            avg_suppressor_amount /= total_weight

        # Pick most frequent types (weighted)
        best_solidifier = max(solidifier_counts, key=solidifier_counts.get) if solidifier_counts else "普通ポルトランドセメント"
        best_suppressor = max(suppressor_counts, key=suppressor_counts.get) if suppressor_counts else ""

        # Adjust based on severity difference
        mean_nearest_severity = sum(
            _severity_score(r["analysis"]) for _, r in nearest
        ) / len(nearest) if nearest else 0

        severity_ratio = (severity + 0.1) / (mean_nearest_severity + 0.1)
        adjusted_solidifier = round(avg_solidifier_amount * min(severity_ratio, 1.5))
        adjusted_suppressor = round(avg_suppressor_amount * min(severity_ratio, 1.5), 1)

        # Confidence based on nearest distance and pass rate
        avg_distance = sum(d for d, _ in nearest) / len(nearest) if nearest else 1.0
        pass_count = sum(
            1 for _, r in nearest
            if r.get("elutionResult", {}).get("passed")
        )
        pass_rate = pass_count / len(nearest) if nearest else 0

        confidence = max(0.1, min(0.95,
            (1.0 - min(avg_distance, 1.0)) * 0.5 + pass_rate * 0.5
        ))

        reasoning.append(f"類似実績 {len(nearest)} 件から推奨 (平均距離: {avg_distance:.3f})")
        reasoning.append(f"過去の合格率: {pass_rate*100:.0f}%")
        if severity_ratio > 1.1:
            reasoning.append(f"汚染度が類似実績より高いため添加量を{(severity_ratio-1)*100:.0f}%増量")

        return {
            "recommendation": {
                "solidifierType": best_solidifier,
                "solidifierAmount": adjusted_solidifier,
                "solidifierUnit": "kg/t",
                "suppressorType": best_suppressor,
                "suppressorAmount": adjusted_suppressor,
                "suppressorUnit": "kg/t",
            },
            "confidence": round(confidence, 2),
            "method": "similarity",
            "reasoning": reasoning,
            "similarRecords": similar_records,
        }

    # Fallback: rule-based recommendation
    reasoning.append("過去実績が不足のためルールベースで推奨")
    rec = _rule_based_recommendation(analysis, waste_type)
    confidence = 0.4 if not exceeding else 0.3

    return {
        "recommendation": rec,
        "confidence": round(confidence, 2),
        "method": "rule",
        "reasoning": reasoning,
        "similarRecords": [],
    }
