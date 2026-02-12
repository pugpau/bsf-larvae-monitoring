"""Batch job management API — list runs, trigger jobs, check scheduler status."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.batch.jobs import JOB_REGISTRY
from src.batch.scheduler import get_scheduler_status
from src.batch.schemas import (
    BatchJobListResponse,
    BatchJobRunResponse,
    BatchTriggerResponse,
    SchedulerStatusResponse,
)
from src.database.postgresql import BatchJobRun, get_async_session
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


@router.get("/jobs", response_model=BatchJobListResponse)
async def list_job_runs(
    job_name: Optional[str] = Query(None, description="Filter by job name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
):
    """List batch job run history (newest first)."""
    query = select(BatchJobRun).order_by(BatchJobRun.started_at.desc())
    count_query = select(func.count(BatchJobRun.id))

    if job_name:
        query = query.where(BatchJobRun.job_name == job_name)
        count_query = count_query.where(BatchJobRun.job_name == job_name)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    result = await session.execute(query.offset(offset).limit(limit))
    runs = result.scalars().all()

    return BatchJobListResponse(
        jobs=[
            BatchJobRunResponse(
                id=str(run.id),
                job_name=run.job_name,
                status=run.status,
                started_at=run.started_at.isoformat() if run.started_at else None,
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                result_summary=run.result_summary,
                error_message=run.error_message,
            )
            for run in runs
        ],
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=BatchJobRunResponse)
async def get_job_run(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get details of a specific batch job run."""
    from uuid import UUID

    try:
        uid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    result = await session.execute(
        select(BatchJobRun).where(BatchJobRun.id == uid)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Job run not found")

    return BatchJobRunResponse(
        id=str(run.id),
        job_name=run.job_name,
        status=run.status,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        result_summary=run.result_summary,
        error_message=run.error_message,
    )


@router.post("/trigger/{job_name}", response_model=BatchTriggerResponse)
async def trigger_job(
    job_name: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Manually trigger a batch job by name."""
    if job_name not in JOB_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown job: {job_name}",
        )

    logger.info(f"Manual trigger: {job_name}")
    job_fn = JOB_REGISTRY[job_name]

    try:
        await job_fn()
        # Find the latest run ID for this job
        latest = await session.execute(
            select(BatchJobRun)
            .where(BatchJobRun.job_name == job_name)
            .order_by(BatchJobRun.started_at.desc())
            .limit(1)
        )
        run = latest.scalar_one_or_none()
        run_id = str(run.id) if run else "unknown"

        return BatchTriggerResponse(
            message=f"Job '{job_name}' completed successfully",
            job_run_id=run_id,
        )
    except Exception as e:
        logger.error(f"Manual trigger failed: {job_name} — {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Job '{job_name}' failed. Check server logs for details.",
        )


@router.get("/status", response_model=SchedulerStatusResponse)
async def scheduler_status():
    """Get scheduler running state and next run times."""
    return get_scheduler_status()
