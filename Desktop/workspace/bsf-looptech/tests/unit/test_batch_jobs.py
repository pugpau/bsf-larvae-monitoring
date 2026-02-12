"""Unit tests for batch job functions."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.batch.jobs import daily_aggregation, monthly_report, weekly_ml_retrain
from src.database.postgresql import BatchJobRun, WasteRecord


@pytest.mark.asyncio
class TestDailyAggregation:
    """Tests for daily_aggregation job."""

    async def test_empty_db(self, async_session):
        """Should succeed with zero records."""
        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await daily_aggregation()

        assert result["total_records"] == 0
        assert result["violations_count"] == 0
        assert "date" in result

        # Verify job run was recorded
        runs = await async_session.execute(
            select(BatchJobRun).where(BatchJobRun.job_name == "daily_aggregation")
        )
        run = runs.scalar_one()
        assert run.status == "success"

    async def test_with_records(self, async_session):
        """Should count records from the last day."""
        # Insert test records
        for i in range(3):
            record = WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=datetime.utcnow() - timedelta(hours=12),
                waste_type="汚泥",
                status="formulated",
            )
            async_session.add(record)
        await async_session.commit()

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await daily_aggregation()

        assert result["total_records"] == 3
        assert result["status_counts"]["formulated"] == 3

    async def test_threshold_violation(self, async_session):
        """Should detect elution threshold violations."""
        record = WasteRecord(
            id=uuid.uuid4(),
            source="工場A",
            delivery_date=datetime.utcnow() - timedelta(hours=6),
            waste_type="汚泥",
            status="tested",
            elution_result={"Pb": 0.05, "As": 0.002},  # Pb exceeds 0.01
        )
        async_session.add(record)
        await async_session.commit()

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await daily_aggregation()

        assert result["violations_count"] == 1
        assert result["violations"][0]["metal"] == "Pb"
        assert result["violations"][0]["value"] == 0.05

    async def test_old_records_excluded(self, async_session):
        """Records older than 1 day should not be counted."""
        old_record = WasteRecord(
            id=uuid.uuid4(),
            source="工場B",
            delivery_date=datetime.utcnow() - timedelta(days=3),
            waste_type="汚泥",
            status="pending",
        )
        async_session.add(old_record)
        await async_session.commit()

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await daily_aggregation()

        assert result["total_records"] == 0

    async def test_job_failure_recorded(self, async_session):
        """When an error occurs, it should be recorded in batch_job_runs."""
        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # Patch to raise error after job start recording
            with patch(
                "src.batch.jobs.select",
                side_effect=[
                    # First call (count) succeeds via original
                    Exception("DB connection lost"),
                ],
            ):
                # The job catches and re-raises after recording failure
                with pytest.raises(Exception, match="DB connection lost"):
                    await daily_aggregation()

        runs = await async_session.execute(
            select(BatchJobRun).where(BatchJobRun.job_name == "daily_aggregation")
        )
        run = runs.scalar_one()
        assert run.status == "failed"
        assert "DB connection lost" in run.error_message


@pytest.mark.asyncio
class TestWeeklyMLRetrain:
    """Tests for weekly_ml_retrain job."""

    async def test_insufficient_data(self, async_session):
        """Should skip retraining when data is insufficient (< 10 records)."""
        mock_extract = AsyncMock(return_value=(MagicMock(spec=["__len__"], __len__=lambda s: 5), []))

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("src.ml.data_pipeline.extract_training_data", mock_extract):
                result = await weekly_ml_retrain()

        assert result["skipped"] is True
        assert "Insufficient data" in result["reason"]

    async def test_success(self, async_session):
        """Should train and register models when sufficient data exists."""
        import pandas as pd

        # Create mock training data with 60 rows
        mock_df = pd.DataFrame({
            "pH": [7.0] * 60,
            "moisture": [50.0] * 60,
            "formulation_type": ["cement"] * 60,
        })
        mock_extract = AsyncMock(return_value=(mock_df, []))

        mock_trainer = MagicMock()
        mock_trainer.train.return_value = {
            "classifier": {"accuracy": 0.85},
            "regressor": {"r2": 0.78},
        }
        mock_trainer.save.return_value = {
            "classifier": "/models/cls_v1.pkl",
            "regressor": "/models/reg_v1.pkl",
        }

        mock_registry = MagicMock()
        mock_registry.get_next_version = AsyncMock(return_value=1)
        mock_model = MagicMock()
        mock_model.id = uuid.uuid4()
        mock_registry.register_model = AsyncMock(return_value=mock_model)
        mock_registry.activate_model = AsyncMock()

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            with (
                patch("src.ml.data_pipeline.extract_training_data", mock_extract),
                patch("src.ml.trainer.FormulationTrainer", return_value=mock_trainer),
                patch("src.ml.model_registry.ModelRegistry", return_value=mock_registry),
            ):
                result = await weekly_ml_retrain()

        assert result["skipped"] is False
        assert result["real_records"] == 60
        assert result["classifier_version"] == 1
        mock_trainer.train.assert_called_once()
        assert mock_registry.activate_model.call_count == 2


@pytest.mark.asyncio
class TestMonthlyReport:
    """Tests for monthly_report job."""

    async def test_empty_month(self, async_session):
        """Should generate report with zero values for empty month."""
        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await monthly_report()

        assert result["total_records"] == 0
        assert result["success_rate"] == 0.0
        assert result["ml_usage_rate"] == 0.0
        assert "period" in result

    async def test_with_records(self, async_session):
        """Should calculate correct statistics from waste records."""
        now = datetime.utcnow()
        prev_month = (now.replace(day=1) - timedelta(days=1)).replace(day=15)

        for i, status in enumerate(["formulated", "formulated", "pending", "tested"]):
            record = WasteRecord(
                id=uuid.uuid4(),
                source=f"工場{i}",
                delivery_date=prev_month,
                waste_type="汚泥",
                status=status,
            )
            async_session.add(record)
        await async_session.commit()

        with patch("src.batch.jobs.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=async_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await monthly_report()

        assert result["total_records"] == 4
        # formulated(2) + tested(1) = 3 successes out of 4
        assert result["success_rate"] == 75.0
