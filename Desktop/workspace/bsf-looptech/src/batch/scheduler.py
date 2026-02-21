"""APScheduler setup — initializes and manages the async job scheduler."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.batch.jobs import daily_aggregation, monthly_report, weekly_ml_retrain
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.BATCH_TIMEZONE)


def init_scheduler() -> None:
    """Register jobs and start the scheduler (if BATCH_ENABLED)."""
    if not settings.BATCH_ENABLED:
        logger.info("Batch scheduler disabled (BATCH_ENABLED=false)")
        return

    scheduler.add_job(
        daily_aggregation,
        CronTrigger(hour=3, minute=0),
        id="daily_aggregation",
        name="日次データ集計",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_ml_retrain,
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_ml_retrain",
        name="週次ML再学習",
        replace_existing=True,
    )
    scheduler.add_job(
        monthly_report,
        CronTrigger(day=1, hour=4, minute=0),
        id="monthly_report",
        name="月次統計レポート",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Batch scheduler started (timezone={settings.BATCH_TIMEZONE}, 3 jobs registered)"
    )


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Batch scheduler shut down")


def get_scheduler_status() -> dict:
    """Return scheduler state and next run times for all jobs."""
    jobs_info = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name or job.id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            })
    return {
        "running": scheduler.running,
        "jobs": jobs_info,
    }
