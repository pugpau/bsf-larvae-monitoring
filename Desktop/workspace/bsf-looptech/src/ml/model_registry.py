"""Model registry: manages ML model versions in database and filesystem."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import MLModel, MLPrediction

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Manages ML model lifecycle: registration, activation, prediction logging."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_model(
        self,
        name: str,
        model_type: str,
        version: int,
        file_path: str,
        training_records: int,
        feature_columns: List[str],
        target_columns: List[str],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Register a new model version in the database."""
        model = MLModel(
            id=uuid.uuid4(),
            name=name,
            model_type=model_type,
            version=version,
            file_path=file_path,
            training_records=training_records,
            feature_columns=feature_columns,
            target_columns=target_columns,
            metrics=metrics,
            is_active=False,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return _model_to_dict(model)

    async def activate_model(self, model_id: str) -> bool:
        """Activate a model, deactivating others of the same type."""
        # Get the model to find its type
        result = await self.session.execute(
            select(MLModel).where(MLModel.id == uuid.UUID(model_id))
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        # Deactivate all models of same type
        await self.session.execute(
            update(MLModel)
            .where(MLModel.model_type == model.model_type)
            .values(is_active=False)
        )
        # Activate the target
        model.is_active = True
        await self.session.commit()
        return True

    async def get_active_model(self, model_type: str) -> Optional[Dict[str, Any]]:
        """Return the currently active model metadata for a given type."""
        result = await self.session.execute(
            select(MLModel).where(
                MLModel.model_type == model_type,
                MLModel.is_active == True,  # noqa: E712
            )
        )
        model = result.scalar_one_or_none()
        return _model_to_dict(model) if model else None

    async def list_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered models, optionally filtered by type."""
        query = select(MLModel).order_by(MLModel.created_at.desc())
        if model_type:
            query = query.where(MLModel.model_type == model_type)
        result = await self.session.execute(query)
        return [_model_to_dict(m) for m in result.scalars().all()]

    async def get_next_version(self, model_type: str) -> int:
        """Get the next version number for a model type."""
        result = await self.session.execute(
            select(func.max(MLModel.version)).where(MLModel.model_type == model_type)
        )
        current = result.scalar()
        return (current or 0) + 1

    async def log_prediction(
        self,
        input_features: Dict[str, Any],
        prediction: Dict[str, Any],
        method: str,
        confidence: float,
        waste_record_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log a prediction for audit and accuracy tracking."""
        pred = MLPrediction(
            id=uuid.uuid4(),
            waste_record_id=uuid.UUID(waste_record_id) if waste_record_id else None,
            model_id=uuid.UUID(model_id) if model_id else None,
            input_features=input_features,
            prediction=prediction,
            method=method,
            confidence=confidence,
        )
        self.session.add(pred)
        await self.session.commit()
        return {"id": str(pred.id), "method": method, "confidence": confidence}

    async def get_prediction_accuracy(self, days: int = 30) -> Dict[str, Any]:
        """Calculate prediction accuracy metrics over the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(MLPrediction).where(
                MLPrediction.created_at >= cutoff,
                MLPrediction.actual_passed.isnot(None),
            )
        )
        predictions = result.scalars().all()

        if not predictions:
            return {"total": 0, "ml": {}, "rule": {}, "similarity": {}}

        by_method: Dict[str, list] = {}
        for p in predictions:
            method = p.method
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(p.actual_passed)

        stats: Dict[str, Any] = {"total": len(predictions)}
        for method, outcomes in by_method.items():
            total = len(outcomes)
            passed = sum(1 for o in outcomes if o)
            stats[method] = {
                "count": total,
                "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
            }
        return stats

    async def get_trend_data(self, months: int = 6) -> List[Dict[str, Any]]:
        """Get monthly aggregated prediction data for trend charts."""
        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        result = await self.session.execute(
            select(MLPrediction).where(MLPrediction.created_at >= cutoff)
            .order_by(MLPrediction.created_at)
        )
        predictions = result.scalars().all()

        # Group by month
        monthly: Dict[str, Dict[str, Any]] = {}
        for p in predictions:
            key = p.created_at.strftime("%Y-%m")
            if key not in monthly:
                monthly[key] = {"month": key, "total": 0, "ml": 0, "rule": 0,
                                "similarity": 0, "passed": 0, "with_outcome": 0}
            monthly[key]["total"] += 1
            monthly[key][p.method] = monthly[key].get(p.method, 0) + 1
            if p.actual_passed is not None:
                monthly[key]["with_outcome"] += 1
                if p.actual_passed:
                    monthly[key]["passed"] += 1

        return list(monthly.values())


def _model_to_dict(model: MLModel) -> Dict[str, Any]:
    """Convert MLModel ORM object to dict."""
    return {
        "id": str(model.id),
        "name": model.name,
        "model_type": model.model_type,
        "version": model.version,
        "file_path": model.file_path,
        "training_records": model.training_records,
        "feature_columns": model.feature_columns,
        "target_columns": model.target_columns,
        "metrics": model.metrics,
        "is_active": model.is_active,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }
