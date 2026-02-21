"""Unified prediction interface with ML→similarity→rule fallback chain.

Loads trained ML models and falls back to the existing recommender engine
when ML predictions are unavailable or low-confidence.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.ml.feature_engineering import (
    ANALYSIS_FEATURES,
    add_derived_features,
    encode_waste_type,
    impute_missing,
)
from src.ml.model_registry import ModelRegistry
from src.ml.trainer import FormulationTrainer
from src.waste.recommender import recommend_formulation, ELUTION_LIMITS

logger = logging.getLogger(__name__)

# Minimum confidence threshold for ML predictions
ML_CONFIDENCE_THRESHOLD = 0.5


class FormulationPredictor:
    """Unified prediction: ML-first with recommender.py fallback."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = ModelRegistry(session)
        self._trainer: Optional[FormulationTrainer] = None
        self._loaded = False

    async def _ensure_loaded(self) -> bool:
        """Load active models from registry if not already loaded."""
        if self._loaded:
            return self._trainer is not None and self._trainer.classifier is not None

        cls_meta = await self.registry.get_active_model("classifier")
        if not cls_meta:
            self._loaded = True
            return False

        try:
            directory = os.path.dirname(cls_meta["file_path"])
            version = cls_meta["version"]
            self._trainer = FormulationTrainer.load(directory, version)
            self._loaded = True
            logger.info(f"Loaded ML models v{version} from {directory}")
            return self._trainer.classifier is not None
        except Exception as e:
            logger.warning(f"Failed to load ML models: {e}")
            self._loaded = True
            return False

    async def predict(
        self,
        analysis: Dict[str, Any],
        waste_type: str,
        history: Optional[List[Dict[str, Any]]] = None,
        waste_record_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Predict optimal formulation with fallback chain.

        1. If ML model available → ML prediction
        2. If ML fails or confidence < threshold → similarity-based
        3. If insufficient history → rule-based

        Always logs prediction.
        """
        ml_available = await self._ensure_loaded()

        # Try ML prediction
        if ml_available:
            try:
                result = self._ml_predict(analysis, waste_type)
                if result and result.get("confidence", 0) >= ML_CONFIDENCE_THRESHOLD:
                    await self._log(analysis, result, waste_record_id)
                    return result
            except Exception as e:
                logger.warning(f"ML prediction failed, falling back: {e}")

        # Fallback to existing recommender
        result = recommend_formulation(analysis, waste_type, history or [])
        await self._log(analysis, result, waste_record_id)
        return result

    def _ml_predict(self, analysis: Dict[str, Any], waste_type: str) -> Optional[Dict[str, Any]]:
        """Generate prediction using trained ML models."""
        if not self._trainer:
            return None

        # Build feature DataFrame
        row = {k: analysis.get(k) for k in ANALYSIS_FEATURES}
        row["waste_type"] = waste_type
        df = pd.DataFrame([row])
        df = add_derived_features(df)
        df = impute_missing(df)
        df, _ = encode_waste_type(df)

        # Align columns with training features
        for col in self._trainer.feature_columns:
            if col not in df.columns:
                df[col] = 0
        df = df[self._trainer.feature_columns]

        # Classification prediction
        cls_result = self._trainer.predict_classification(df)
        reg_result = self._trainer.predict_regression(df)

        if not cls_result and not reg_result:
            return None

        solidifier_type = cls_result.get("solidifier_type", "普通ポルトランドセメント") if cls_result else "普通ポルトランドセメント"
        solidifier_amount = reg_result.get("solidifier_amount", 150.0) if reg_result else 150.0

        # Confidence from model metrics
        cls_metrics = self._trainer.metrics.get("classifier", {})
        reg_metrics = self._trainer.metrics.get("regressor", {})
        confidence = (cls_metrics.get("accuracy", 0.5) + max(0, reg_metrics.get("r2", 0.5))) / 2

        recommendation = {
            "solidifierType": solidifier_type,
            "solidifierAmount": round(solidifier_amount, 1),
            "solidifierUnit": "kg/t",
            "suppressorType": "",
            "suppressorAmount": 0.0,
            "suppressorUnit": "kg/t",
        }

        return {
            "recommendation": recommendation,
            "confidence": round(confidence, 4),
            "method": "ml",
            "reasoning": [
                f"ML予測（RandomForest v{self._trainer.metrics.get('version', '?')}）",
                f"分類精度: {cls_metrics.get('accuracy', 'N/A')}",
                f"回帰R²: {reg_metrics.get('r2', 'N/A')}",
            ],
            "model_version": self._trainer.metrics.get("version"),
            "similarRecords": [],
        }

    async def predict_elution(
        self,
        analysis: Dict[str, Any],
        formulation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Predict whether a formulation will pass elution tests.

        Uses a heuristic based on analysis severity and formulation strength.
        """
        # Calculate metal severity
        severity = 0.0
        metal_predictions: Dict[str, float] = {}
        for metal, limit in ELUTION_LIMITS.items():
            val = analysis.get(metal, 0.0)
            if val is not None and limit > 0:
                ratio = val / limit
                metal_predictions[metal] = round(ratio, 3)
                if ratio > 1.0:
                    severity += ratio - 1.0

        solidifier_amount = formulation.get("solidifierAmount", 0)
        effectiveness = min(1.0, solidifier_amount / 200.0)
        pass_probability = max(0.0, min(1.0, effectiveness * 0.8 - severity * 0.15 + 0.15))

        passed = pass_probability >= 0.5
        reasoning = []
        if severity > 0:
            reasoning.append(f"重金属超過度: {severity:.2f}")
        reasoning.append(f"固化材効果: {effectiveness:.1%}")
        reasoning.append(f"合格確率: {pass_probability:.1%}")

        return {
            "passed": passed,
            "confidence": round(pass_probability, 4),
            "method": "heuristic",
            "metal_predictions": metal_predictions,
            "reasoning": reasoning,
        }

    async def _log(
        self,
        analysis: Dict[str, Any],
        result: Dict[str, Any],
        waste_record_id: Optional[str],
    ) -> None:
        """Log prediction for audit trail."""
        try:
            model_meta = await self.registry.get_active_model("classifier")
            model_id = model_meta["id"] if model_meta else None
            await self.registry.log_prediction(
                input_features=analysis,
                prediction=result.get("recommendation", {}),
                method=result.get("method", "unknown"),
                confidence=result.get("confidence", 0.0),
                waste_record_id=waste_record_id,
                model_id=model_id,
            )
        except Exception as e:
            logger.warning(f"Failed to log prediction: {e}")
