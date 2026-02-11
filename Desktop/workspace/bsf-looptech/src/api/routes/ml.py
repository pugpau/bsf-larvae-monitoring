"""ML prediction and model management API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.ml.schemas import (
    PredictionRequest,
    PredictionResponse,
    ElutionPredictionRequest,
    ElutionPredictionResponse,
    TrainingConfig,
    TrainingReport,
)
from src.ml.predictor import FormulationPredictor
from src.ml.model_registry import ModelRegistry
from src.ml.data_pipeline import extract_training_data
from src.ml.synthetic_data import generate_synthetic_records
from src.ml.trainer import FormulationTrainer
from src.config import settings
from src.waste.repository import WasteRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ml"])


# ── Prediction Endpoints ──


@router.post("/predict/formulation", response_model=PredictionResponse)
async def predict_formulation(
    data: PredictionRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Predict optimal formulation. ML-first with rule-based fallback."""
    predictor = FormulationPredictor(session)

    # Fetch history for similarity fallback
    repo = WasteRepository(session)
    history = await repo.get_all(limit=500)

    result = await predictor.predict(
        analysis=data.analysis,
        waste_type=data.waste_type,
        history=history,
        waste_record_id=data.waste_record_id,
    )
    return PredictionResponse(**result)


@router.post("/predict/elution", response_model=ElutionPredictionResponse)
async def predict_elution(
    data: ElutionPredictionRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Predict whether a formulation will pass elution tests."""
    predictor = FormulationPredictor(session)
    result = await predictor.predict_elution(
        analysis=data.analysis,
        formulation=data.formulation,
    )
    return ElutionPredictionResponse(**result)


# ── Model Management Endpoints ──


@router.get("/ml/models")
async def list_models(
    model_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """List all registered ML models."""
    registry = ModelRegistry(session)
    return await registry.list_models(model_type=model_type)


@router.post("/ml/train", response_model=TrainingReport)
async def trigger_training(
    config: Optional[TrainingConfig] = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Trigger model retraining. Returns training report."""
    cfg = config or TrainingConfig()

    # 1. Extract real data
    real_df, warnings = await extract_training_data(session)
    real_count = len(real_df)

    # 2. Generate synthetic data if needed
    import pandas as pd
    synthetic_count = 0
    if cfg.include_synthetic and real_count < 50:
        synthetic = generate_synthetic_records(n=cfg.synthetic_count, seed=cfg.random_state)
        synthetic_df = pd.DataFrame(synthetic)
        synthetic_count = len(synthetic_df)
        if real_count > 0:
            df = pd.concat([real_df, synthetic_df], ignore_index=True)
        else:
            df = synthetic_df
    elif real_count > 0:
        df = real_df
    else:
        return TrainingReport(
            success=False,
            real_records=0,
            synthetic_records=0,
            total_records=0,
            warnings=["No training data available. Add waste records with formulations first."],
        )

    # 3. Train models
    trainer = FormulationTrainer(cfg)
    metrics = trainer.train(df)

    if "error" in metrics:
        return TrainingReport(
            success=False,
            real_records=real_count,
            synthetic_records=synthetic_count,
            total_records=len(df),
            warnings=[metrics["error"]],
        )

    # 4. Save and register models
    registry = ModelRegistry(session)
    cls_version = await registry.get_next_version("classifier")
    reg_version = await registry.get_next_version("regressor")

    model_dir = settings.MODEL_REGISTRY_PATH
    paths = trainer.save(model_dir, version=cls_version)

    model_ids = {}

    if "classifier" in paths:
        cls_model = await registry.register_model(
            name=f"classifier_v{cls_version}",
            model_type="classifier",
            version=cls_version,
            file_path=paths["classifier"],
            training_records=len(df),
            feature_columns=trainer.feature_columns,
            target_columns=trainer.cls_targets,
            metrics=metrics.get("classifier", {}),
        )
        await registry.activate_model(cls_model["id"])
        model_ids["classifier"] = cls_model["id"]

    if "regressor" in paths:
        reg_model = await registry.register_model(
            name=f"regressor_v{reg_version}",
            model_type="regressor",
            version=reg_version,
            file_path=paths["regressor"],
            training_records=len(df),
            feature_columns=trainer.feature_columns,
            target_columns=trainer.reg_targets,
            metrics=metrics.get("regressor", {}),
        )
        await registry.activate_model(reg_model["id"])
        model_ids["regressor"] = reg_model["id"]

    return TrainingReport(
        success=True,
        real_records=real_count,
        synthetic_records=synthetic_count,
        total_records=len(df),
        classifier_metrics=metrics.get("classifier", {}),
        regressor_metrics=metrics.get("regressor", {}),
        model_ids=model_ids,
        warnings=warnings,
    )


@router.put("/ml/models/{model_id}/activate")
async def activate_model(
    model_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Activate a specific model version."""
    registry = ModelRegistry(session)
    success = await registry.activate_model(model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"status": "activated", "model_id": model_id}


# ── Analytics Endpoints ──


@router.get("/ml/accuracy")
async def get_accuracy(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_async_session),
):
    """Get prediction accuracy metrics over time window."""
    registry = ModelRegistry(session)
    return await registry.get_prediction_accuracy(days=days)


@router.get("/ml/trends")
async def get_trends(
    months: int = Query(6, ge=1, le=24),
    session: AsyncSession = Depends(get_async_session),
):
    """Get monthly trend data for dashboard charts."""
    registry = ModelRegistry(session)
    return await registry.get_trend_data(months=months)
