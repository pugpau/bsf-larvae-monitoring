"""Pydantic schemas for activity log module."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActivityLogCreate(BaseModel):
    """Internal schema for creating an activity log entry."""

    event_type: str = Field(..., max_length=50)
    entity_type: str = Field(..., max_length=50)
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str = Field(..., max_length=50)
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    severity: str = Field(default="info", pattern="^(info|warning|critical)$")
    metadata_json: Optional[Dict[str, Any]] = None


class ActivityLogResponse(BaseModel):
    """Response schema for a single activity log entry."""

    id: str
    event_type: str
    entity_type: str
    entity_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    title: str
    description: Optional[str] = None
    severity: str
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityFeedResponse(BaseModel):
    """Paginated activity feed response."""

    items: List[ActivityLogResponse]
    total: int
    limit: int
    offset: int
