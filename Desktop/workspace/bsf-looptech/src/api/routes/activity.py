"""Activity feed API — paginated activity logs with filtering."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.activity.service import ActivityService
from src.database.postgresql import get_async_session
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


@router.get("/feed")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, max_length=50),
    entity_type: Optional[str] = Query(None, max_length=50),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    session: AsyncSession = Depends(get_async_session),
):
    """Get paginated activity feed, newest first."""
    service = ActivityService(session)
    return await service.get_feed(
        limit=limit,
        offset=offset,
        event_type=event_type,
        entity_type=entity_type,
        severity=severity,
    )


@router.get("/{entity_type}/{entity_id}")
async def get_entity_activity(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """Get activity logs for a specific entity."""
    service = ActivityService(session)
    items = await service.get_entity_activity(entity_type, entity_id, limit)
    return {"items": items, "total": len(items)}
