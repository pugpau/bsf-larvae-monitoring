"""Feature engineering for ML pipeline.

Transforms raw waste analysis data into ML-ready feature matrices.
Reuses constants from recommender.py to ensure consistency.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.waste.recommender import ELUTION_LIMITS, FEATURE_WEIGHTS

# Base analysis features expected from waste_records.analysis JSON
ANALYSIS_FEATURES = ["pH", "moisture", "ignitionLoss",
                     "Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]

METAL_FEATURES = ["Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]


def severity_score(row: pd.Series) -> float:
    """Compute regulatory severity: sum of weighted exceedance ratios.

    For each metal, if concentration > limit, add (conc/limit - 1) * weight.
    Returns 0.0 for fully compliant samples.
    """
    score = 0.0
    for metal, limit in ELUTION_LIMITS.items():
        val = row.get(metal, 0.0)
        if pd.isna(val) or limit == 0:
            continue
        ratio = val / limit
        if ratio > 1.0:
            weight = FEATURE_WEIGHTS.get(metal, 1.0)
            score += (ratio - 1.0) * weight
    return score


def metal_count_exceeded(row: pd.Series) -> int:
    """Count how many metals exceed their regulatory limits."""
    count = 0
    for metal, limit in ELUTION_LIMITS.items():
        val = row.get(metal, 0.0)
        if pd.notna(val) and val > limit:
            count += 1
    return count


def max_exceedance_ratio(row: pd.Series) -> float:
    """Maximum ratio of any metal concentration to its limit."""
    max_ratio = 0.0
    for metal, limit in ELUTION_LIMITS.items():
        val = row.get(metal, 0.0)
        if pd.notna(val) and limit > 0:
            max_ratio = max(max_ratio, val / limit)
    return max_ratio


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived feature columns to a DataFrame of analysis data.

    Added columns:
    - severity_score: weighted sum of regulatory exceedances
    - metal_count_exceeded: number of metals over limits
    - max_exceedance_ratio: worst metal-to-limit ratio
    - ph_deviation: absolute deviation from neutral pH (7.0)
    - moisture_high: binary flag for moisture > 60%
    """
    result = df.copy()
    result["severity_score"] = result.apply(severity_score, axis=1)
    result["metal_count_exceeded"] = result.apply(metal_count_exceeded, axis=1)
    result["max_exceedance_ratio"] = result.apply(max_exceedance_ratio, axis=1)

    if "pH" in result.columns:
        result["ph_deviation"] = result["pH"].fillna(7.0).sub(7.0).abs()
    else:
        result["ph_deviation"] = 0.0

    if "moisture" in result.columns:
        result["moisture_high"] = (result["moisture"].fillna(0) > 60).astype(int)
    else:
        result["moisture_high"] = 0

    return result


def encode_waste_type(df: pd.DataFrame, col: str = "waste_type") -> Tuple[pd.DataFrame, List[str]]:
    """One-hot encode waste_type column.

    Returns (encoded_df, list_of_new_column_names).
    Original column is dropped.
    """
    if col not in df.columns:
        return df, []

    dummies = pd.get_dummies(df[col], prefix="wt", dtype=int)
    new_cols = list(dummies.columns)
    result = pd.concat([df.drop(columns=[col]), dummies], axis=1)
    return result, new_cols


def impute_missing(df: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
    """Fill missing numeric values with column median. Remaining NaN → 0."""
    result = df.copy()
    cols = columns or [c for c in ANALYSIS_FEATURES if c in result.columns]
    for col in cols:
        if col in result.columns:
            median_val = result[col].median()
            if pd.notna(median_val):
                result[col] = result[col].fillna(median_val)
    result = result.fillna(0)
    return result


def prepare_features_and_targets(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Split DataFrame into feature matrix X, classification targets, regression targets.

    Classification targets: solidifier_type, suppressant_type
    Regression targets: solidifier_amount, suppressant_amount

    Returns (X, y_cls, y_reg) where y_cls/y_reg may be None if columns missing.
    """
    cls_cols = [c for c in ["solidifier_type", "suppressant_type"] if c in df.columns]
    reg_cols = [c for c in ["solidifier_amount", "suppressant_amount"] if c in df.columns]
    non_feature_cols = cls_cols + reg_cols + ["elution_passed"]
    non_feature_cols = [c for c in non_feature_cols if c in df.columns]

    x = df.drop(columns=non_feature_cols, errors="ignore")
    # Drop any remaining string columns
    x = x.select_dtypes(include=[np.number])

    y_cls = df[cls_cols] if cls_cols else None
    y_reg = df[reg_cols].astype(float) if reg_cols else None

    return x, y_cls, y_reg
