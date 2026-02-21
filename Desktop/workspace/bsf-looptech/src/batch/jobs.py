"""Batch job functions — daily aggregation, weekly ML retraining, monthly reports."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    AsyncSessionLocal,
    BatchJobRun,
    MLPrediction,
    WasteRecord,
)
from src.utils.logging import get_logger
from src.waste.service import ELUTION_THRESHOLDS

logger = get_logger(__name__)


async def _record_job_start(session: AsyncSession, job_name: str) -> BatchJobRun:
    """Create a batch_job_runs record with status=running."""
    run = BatchJobRun(job_name=job_name, status="running")
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def _record_job_end(
    session: AsyncSession,
    run: BatchJobRun,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Update batch_job_runs record with completion info."""
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    run.result_summary = result
    run.error_message = error
    await session.commit()


async def daily_aggregation() -> dict[str, Any]:
    """Daily data aggregation — count records and check threshold violations.

    Runs at 03:00 JST daily.
    """
    logger.info("Batch: daily_aggregation started")
    async with AsyncSessionLocal() as session:
        run = await _record_job_start(session, "daily_aggregation")
        try:
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)

            # Count today's waste records
            total_result = await session.execute(
                select(func.count(WasteRecord.id)).where(
                    WasteRecord.delivery_date >= yesterday
                )
            )
            total_count = total_result.scalar() or 0

            # Count by status
            status_result = await session.execute(
                select(WasteRecord.status, func.count(WasteRecord.id))
                .where(WasteRecord.delivery_date >= yesterday)
                .group_by(WasteRecord.status)
            )
            status_counts = {row[0]: row[1] for row in status_result.all()}

            # Check threshold violations in elution results
            violations: list[dict[str, Any]] = []
            records_with_elution = await session.execute(
                select(WasteRecord).where(
                    WasteRecord.delivery_date >= yesterday,
                    WasteRecord.elution_result.isnot(None),
                )
            )
            for record in records_with_elution.scalars():
                elution = record.elution_result or {}
                for metal, threshold in ELUTION_THRESHOLDS.items():
                    value = elution.get(metal)
                    if value is not None and value > threshold:
                        violations.append({
                            "record_id": str(record.id),
                            "source": record.source,
                            "metal": metal,
                            "value": value,
                            "threshold": threshold,
                        })

            result = {
                "date": yesterday.strftime("%Y-%m-%d"),
                "total_records": total_count,
                "status_counts": status_counts,
                "violations_count": len(violations),
                "violations": violations[:20],  # cap at 20 for summary
            }

            await _record_job_end(session, run, "success", result=result)
            logger.info(
                f"Batch: daily_aggregation completed — "
                f"{total_count} records, {len(violations)} violations"
            )
            return result

        except Exception as e:
            logger.error(f"Batch: daily_aggregation failed — {e}")
            await _record_job_end(session, run, "failed", error=str(e))
            raise


async def weekly_ml_retrain() -> dict[str, Any]:
    """Weekly ML model retraining — re-train RandomForest if sufficient data exists.

    Runs at 02:00 JST every Sunday.
    """
    logger.info("Batch: weekly_ml_retrain started")
    async with AsyncSessionLocal() as session:
        run = await _record_job_start(session, "weekly_ml_retrain")
        try:
            from src.ml.data_pipeline import extract_training_data
            from src.ml.model_registry import ModelRegistry
            from src.ml.schemas import TrainingConfig
            from src.ml.synthetic_data import generate_synthetic_records
            from src.ml.trainer import FormulationTrainer
            from src.config import settings

            # Extract real training data
            real_df, warnings = await extract_training_data(session)
            real_count = len(real_df)

            if real_count < 10:
                result = {
                    "skipped": True,
                    "reason": f"Insufficient data ({real_count} records, need 10+)",
                    "warnings": warnings,
                }
                await _record_job_end(session, run, "success", result=result)
                logger.info(f"Batch: weekly_ml_retrain skipped — {real_count} records")
                return result

            # Augment with synthetic data if needed
            cfg = TrainingConfig()
            df = real_df
            if real_count < 50:
                synthetic = generate_synthetic_records(n=cfg.synthetic_count)
                import pandas as pd
                df = pd.concat([real_df, synthetic], ignore_index=True)

            # Train
            trainer = FormulationTrainer(cfg)
            metrics = trainer.train(df)

            # Save and register models
            model_dir = settings.MODEL_REGISTRY_PATH
            registry = ModelRegistry(session)
            cls_version = await registry.get_next_version("classifier")
            paths = trainer.save(model_dir, version=cls_version)

            # Register classifier
            cls_model = await registry.register_model(
                name="formulation_classifier",
                model_type="classifier",
                version=cls_version,
                file_path=paths.get("classifier", ""),
                training_records=len(df),
                metrics=metrics.get("classifier", {}),
                feature_columns=list(df.columns),
            )

            # Register regressor
            reg_version = await registry.get_next_version("regressor")
            reg_model = await registry.register_model(
                name="formulation_regressor",
                model_type="regressor",
                version=reg_version,
                file_path=paths.get("regressor", ""),
                training_records=len(df),
                metrics=metrics.get("regressor", {}),
                feature_columns=list(df.columns),
            )

            # Activate new models
            if cls_model:
                await registry.activate_model(str(cls_model.id))
            if reg_model:
                await registry.activate_model(str(reg_model.id))

            result = {
                "skipped": False,
                "real_records": real_count,
                "total_records": len(df),
                "classifier_version": cls_version,
                "regressor_version": reg_version,
                "metrics": metrics,
                "warnings": warnings,
            }

            await _record_job_end(session, run, "success", result=result)
            logger.info(
                f"Batch: weekly_ml_retrain completed — "
                f"v{cls_version} classifier, v{reg_version} regressor"
            )
            return result

        except Exception as e:
            logger.error(f"Batch: weekly_ml_retrain failed — {e}")
            await _record_job_end(session, run, "failed", error=str(e))
            raise


async def monthly_report() -> dict[str, Any]:
    """Monthly statistics report — processing volume, success rate, ML usage.

    Runs at 04:00 JST on the 1st of each month.
    """
    logger.info("Batch: monthly_report started")
    async with AsyncSessionLocal() as session:
        run = await _record_job_start(session, "monthly_report")
        try:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

            # Total waste records last month
            total_result = await session.execute(
                select(func.count(WasteRecord.id)).where(
                    WasteRecord.delivery_date >= prev_month_start,
                    WasteRecord.delivery_date < month_start,
                )
            )
            total_records = total_result.scalar() or 0

            # Status breakdown
            status_result = await session.execute(
                select(WasteRecord.status, func.count(WasteRecord.id))
                .where(
                    WasteRecord.delivery_date >= prev_month_start,
                    WasteRecord.delivery_date < month_start,
                )
                .group_by(WasteRecord.status)
            )
            status_counts = {row[0]: row[1] for row in status_result.all()}

            # Success rate
            formulated = sum(
                v for k, v in status_counts.items()
                if k in ("formulated", "tested", "passed")
            )
            success_rate = (formulated / total_records * 100) if total_records > 0 else 0.0

            # ML predictions last month
            ml_result = await session.execute(
                select(MLPrediction.method, func.count(MLPrediction.id))
                .where(
                    MLPrediction.created_at >= prev_month_start,
                    MLPrediction.created_at < month_start,
                )
                .group_by(MLPrediction.method)
            )
            prediction_counts = {row[0]: row[1] for row in ml_result.all()}
            total_predictions = sum(prediction_counts.values())
            ml_ratio = (
                prediction_counts.get("ml", 0) / total_predictions * 100
                if total_predictions > 0
                else 0.0
            )

            result = {
                "period": prev_month_start.strftime("%Y-%m"),
                "total_records": total_records,
                "status_counts": status_counts,
                "success_rate": round(success_rate, 1),
                "total_predictions": total_predictions,
                "prediction_method_counts": prediction_counts,
                "ml_usage_rate": round(ml_ratio, 1),
            }

            await _record_job_end(session, run, "success", result=result)
            logger.info(
                f"Batch: monthly_report completed — "
                f"{total_records} records, {success_rate:.1f}% success rate"
            )
            return result

        except Exception as e:
            logger.error(f"Batch: monthly_report failed — {e}")
            await _record_job_end(session, run, "failed", error=str(e))
            raise


# Job registry — maps job_name to async function
JOB_REGISTRY: dict[str, Any] = {
    "daily_aggregation": daily_aggregation,
    "weekly_ml_retrain": weekly_ml_retrain,
    "monthly_report": monthly_report,
}
