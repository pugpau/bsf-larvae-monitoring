"""Activity logging service — convenience layer for logging workflow events."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.activity.repository import ActivityLogRepository

logger = logging.getLogger(__name__)


class ActivityService:
    """Convenience wrapper around ActivityLogRepository for structured event logging."""

    def __init__(self, session: AsyncSession):
        self.repo = ActivityLogRepository(session)

    async def log_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str],
        action: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "info",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a single activity event."""
        try:
            return await self.repo.create({
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "action": action,
                "title": title,
                "description": description,
                "severity": severity,
                "metadata_json": metadata,
            })
        except Exception as e:
            # Activity logging should never break the main workflow
            logger.error(f"Failed to log activity event: {e}")
            return {}

    async def get_feed(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated activity feed."""
        return await self.repo.get_feed(
            limit=limit,
            offset=offset,
            event_type=event_type,
            entity_type=entity_type,
            severity=severity,
        )

    async def get_entity_activity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get activity logs for a specific entity."""
        return await self.repo.get_by_entity(entity_type, entity_id, limit)

    # ── Convenience methods for common events ──

    async def log_formulation_event(
        self,
        action: str,
        formulation_id: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "info",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a formulation workflow event."""
        return await self.log_event(
            event_type=f"FORMULATION_{action.upper()}",
            entity_type="formulation",
            entity_id=formulation_id,
            action=action,
            title=title,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata,
        )

    async def log_recipe_event(
        self,
        action: str,
        recipe_id: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "info",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a recipe version/edit event."""
        return await self.log_event(
            event_type=f"RECIPE_{action.upper()}",
            entity_type="recipe",
            entity_id=recipe_id,
            action=action,
            title=title,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata,
        )

    async def log_delivery_event(
        self,
        action: str,
        schedule_id: str,
        title: str,
        description: Optional[str] = None,
        severity: str = "info",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log a delivery schedule event."""
        return await self.log_event(
            event_type=f"DELIVERY_{action.upper()}",
            entity_type="delivery",
            entity_id=schedule_id,
            action=action,
            title=title,
            description=description,
            severity=severity,
            user_id=user_id,
            metadata=metadata,
        )
