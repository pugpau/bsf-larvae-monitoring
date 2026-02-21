"""Pydantic schemas for batch processing API."""

from typing import Any, Optional

from pydantic import BaseModel


class BatchJobRunResponse(BaseModel):
    """Single batch job run record."""

    id: str
    job_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class BatchJobListResponse(BaseModel):
    """Paginated list of batch job runs."""

    jobs: list[BatchJobRunResponse]
    total: int


class BatchTriggerResponse(BaseModel):
    """Response after triggering a batch job."""

    message: str
    job_run_id: str


class SchedulerStatusResponse(BaseModel):
    """Scheduler status with next run times."""

    running: bool
    jobs: list[dict[str, Any]]
