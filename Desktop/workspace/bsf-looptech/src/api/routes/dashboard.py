"""
Dashboard overview API — aggregated stats across modules.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    DeliverySchedule,
    FormulationRecord,
    WasteRecord,
    get_async_session,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_overview(
    session: AsyncSession = Depends(get_async_session),
):
    """Aggregated pipeline overview — status counts across modules."""

    # Delivery schedule status counts
    delivery_result = await session.execute(
        select(
            DeliverySchedule.status,
            func.count().label("count"),
        ).group_by(DeliverySchedule.status)
    )
    delivery_counts = {row[0]: row[1] for row in delivery_result.fetchall()}

    # Formulation record status counts
    formulation_result = await session.execute(
        select(
            FormulationRecord.status,
            func.count().label("count"),
        ).group_by(FormulationRecord.status)
    )
    formulation_counts = {row[0]: row[1] for row in formulation_result.fetchall()}

    # Waste record total + pending
    waste_total_result = await session.execute(
        select(func.count()).select_from(WasteRecord)
    )
    waste_total = waste_total_result.scalar() or 0

    waste_pending_result = await session.execute(
        select(func.count())
        .select_from(WasteRecord)
        .where(WasteRecord.status == "pending")
    )
    waste_pending = waste_pending_result.scalar() or 0

    # Recent activity (last 10)
    recent_activity = []
    try:
        from src.database.postgresql import ActivityLog
        activity_result = await session.execute(
            select(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
            .limit(10)
        )
        for row in activity_result.scalars().all():
            recent_activity.append({
                "id": str(row.id),
                "event_type": row.event_type,
                "entity_type": row.entity_type,
                "action": row.action,
                "title": row.title,
                "severity": row.severity,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })
    except Exception:
        pass  # Activity table may not exist in some test setups

    return {
        "delivery": {
            "scheduled": delivery_counts.get("scheduled", 0),
            "delivered": delivery_counts.get("delivered", 0),
            "cancelled": delivery_counts.get("cancelled", 0),
            "total": sum(delivery_counts.values()),
        },
        "formulation": {
            "proposed": formulation_counts.get("proposed", 0),
            "accepted": formulation_counts.get("accepted", 0),
            "applied": formulation_counts.get("applied", 0),
            "verified": formulation_counts.get("verified", 0),
            "rejected": formulation_counts.get("rejected", 0),
            "total": sum(formulation_counts.values()),
        },
        "waste": {
            "total": waste_total,
            "pending": waste_pending,
        },
        "recent_activity": recent_activity,
    }
