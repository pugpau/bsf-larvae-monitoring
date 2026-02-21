"""Unit tests for batch scheduler."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestScheduler:
    """Tests for scheduler initialization and shutdown."""

    def test_init_enabled(self):
        """Should register 3 jobs and start when BATCH_ENABLED=true."""
        with patch("src.batch.scheduler.settings") as mock_settings:
            mock_settings.BATCH_ENABLED = True
            mock_settings.BATCH_TIMEZONE = "Asia/Tokyo"

            with patch("src.batch.scheduler.scheduler") as mock_scheduler:
                mock_scheduler.running = False
                from src.batch.scheduler import init_scheduler
                init_scheduler()

                assert mock_scheduler.add_job.call_count == 3
                mock_scheduler.start.assert_called_once()

    def test_init_disabled(self):
        """Should not start when BATCH_ENABLED=false."""
        with patch("src.batch.scheduler.settings") as mock_settings:
            mock_settings.BATCH_ENABLED = False

            with patch("src.batch.scheduler.scheduler") as mock_scheduler:
                from src.batch.scheduler import init_scheduler
                init_scheduler()

                mock_scheduler.add_job.assert_not_called()
                mock_scheduler.start.assert_not_called()

    def test_shutdown_running(self):
        """Should shut down when scheduler is running."""
        with patch("src.batch.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.running = True
            from src.batch.scheduler import shutdown_scheduler
            shutdown_scheduler()
            mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_shutdown_not_running(self):
        """Should do nothing when scheduler is not running."""
        with patch("src.batch.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.running = False
            from src.batch.scheduler import shutdown_scheduler
            shutdown_scheduler()
            mock_scheduler.shutdown.assert_not_called()

    def test_get_status_running(self):
        """Should return job info when scheduler is running."""
        mock_job = MagicMock()
        mock_job.id = "daily_aggregation"
        mock_job.name = "日次データ集計"
        mock_job.next_run_time = "2026-02-13 03:00:00+09:00"

        with patch("src.batch.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.running = True
            mock_scheduler.get_jobs.return_value = [mock_job]

            from src.batch.scheduler import get_scheduler_status
            status = get_scheduler_status()

        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "daily_aggregation"

    def test_get_status_stopped(self):
        """Should return empty jobs when scheduler is stopped."""
        with patch("src.batch.scheduler.scheduler") as mock_scheduler:
            mock_scheduler.running = False

            from src.batch.scheduler import get_scheduler_status
            status = get_scheduler_status()

        assert status["running"] is False
        assert status["jobs"] == []
