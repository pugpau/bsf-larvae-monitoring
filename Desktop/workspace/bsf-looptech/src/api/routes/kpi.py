"""KPI dashboard API — realtime metrics, trends, and alerts."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.kpi.schemas import KPIAlertsResponse, KPIRealtimeResponse, KPITrendsResponse
from src.kpi.service import KPIService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/kpi", tags=["kpi"])


@router.get("/realtime", response_model=KPIRealtimeResponse)
async def get_kpi_realtime(
    days: int = Query(7, ge=1, le=90, description="Period in days"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get current KPI values for the specified period."""
    service = KPIService(session)
    return await service.get_realtime(days=days)


@router.get("/trends", response_model=KPITrendsResponse)
async def get_kpi_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get monthly KPI trend data."""
    service = KPIService(session)
    return await service.get_trends(months=months)


@router.get("/alerts", response_model=KPIAlertsResponse)
async def get_kpi_alerts(
    days: int = Query(7, ge=1, le=90, description="Alert window in days"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get active KPI alerts (threshold violations, warnings)."""
    service = KPIService(session)
    return await service.get_alerts(days=days)
