"""Data extraction pipeline: waste_records JSON → flat pandas DataFrame.

Extracts formulated records from the database, flattens JSON columns
(analysis, formulation, elution_result), and validates data quality.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import WasteRecord

logger = logging.getLogger(__name__)

# Minimum non-null analysis features required per record
MIN_FEATURES_PER_RECORD = 4


def flatten_waste_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a single waste_record dict into a flat dict for ML.

    Extracts from nested JSON:
    - analysis.pH → pH, analysis.moisture → moisture, etc.
    - formulation.solidifierType → solidifier_type, etc.
    - elution_result.passed → elution_passed
    """
    flat: Dict[str, Any] = {}

    # Metadata
    flat["waste_type"] = record.get("waste_type", "unknown")
    flat["source"] = record.get("source", "")

    # Analysis features
    analysis = record.get("analysis") or {}
    for key in ["pH", "moisture", "ignitionLoss",
                "Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]:
        val = analysis.get(key)
        flat[key] = float(val) if val is not None else None

    # Formulation targets
    formulation = record.get("formulation") or {}
    flat["solidifier_type"] = formulation.get("solidifierType", "")
    flat["solidifier_amount"] = _to_float(formulation.get("solidifierAmount"))
    flat["suppressant_type"] = formulation.get("suppressorType", "")
    flat["suppressant_amount"] = _to_float(formulation.get("suppressorAmount"))

    # Elution outcome
    elution = record.get("elution_result") or {}
    passed = elution.get("passed")
    flat["elution_passed"] = bool(passed) if passed is not None else None

    return flat


def _to_float(val: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def records_to_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert a list of waste record dicts to a flat DataFrame."""
    rows = [flatten_waste_record(r) for r in records]
    return pd.DataFrame(rows)


def validate_training_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate and clean DataFrame for ML training.

    Drops rows with insufficient features or missing targets.
    Returns (cleaned_df, warnings).
    """
    warnings: List[str] = []
    original_len = len(df)

    if df.empty:
        warnings.append("No data available for training")
        return df, warnings

    # Count non-null analysis features per row
    analysis_cols = [c for c in ["pH", "moisture", "ignitionLoss",
                                  "Pb", "As", "Cd", "Cr6", "Hg", "Se", "F", "B"]
                     if c in df.columns]
    feature_count = df[analysis_cols].notna().sum(axis=1)
    mask = feature_count >= MIN_FEATURES_PER_RECORD
    dropped = (~mask).sum()
    if dropped > 0:
        warnings.append(f"Dropped {dropped} rows with <{MIN_FEATURES_PER_RECORD} analysis features")
    df = df[mask].copy()

    # Drop rows missing formulation targets
    target_cols = ["solidifier_type", "solidifier_amount"]
    for col in target_cols:
        if col in df.columns:
            before = len(df)
            if df[col].dtype == object:
                df = df[df[col].notna() & (df[col] != "")]
            else:
                df = df[df[col].notna()]
            after = len(df)
            if before - after > 0:
                warnings.append(f"Dropped {before - after} rows with missing {col}")

    total_dropped = original_len - len(df)
    if total_dropped > 0:
        warnings.append(f"Total: {len(df)}/{original_len} records usable for training")

    return df, warnings


async def extract_training_data(session: AsyncSession) -> Tuple[pd.DataFrame, List[str]]:
    """Extract formulated waste records from DB and return as flat DataFrame.

    Queries records with status in ('formulated', 'tested', 'passed', 'failed')
    that have both analysis and formulation data.
    Returns (dataframe, warnings).
    """
    query = (
        select(WasteRecord)
        .where(
            WasteRecord.status.in_(["formulated", "tested", "passed", "failed"]),
            WasteRecord.analysis.isnot(None),
            WasteRecord.formulation.isnot(None),
        )
        .order_by(WasteRecord.delivery_date)
    )
    result = await session.execute(query)
    records = result.scalars().all()

    raw_dicts = []
    for rec in records:
        raw_dicts.append({
            "waste_type": rec.waste_type,
            "source": rec.source,
            "analysis": rec.analysis,
            "formulation": rec.formulation,
            "elution_result": rec.elution_result,
        })

    df = records_to_dataframe(raw_dicts)
    df, warnings = validate_training_data(df)

    if len(raw_dicts) > 0:
        logger.info(f"Extracted {len(raw_dicts)} records, {len(df)} usable for training")

    return df, warnings
