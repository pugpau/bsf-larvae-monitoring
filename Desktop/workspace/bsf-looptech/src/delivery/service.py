"""Service layer for delivery schedule status transitions."""

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.activity.service import ActivityService
from src.database.postgresql import DeliverySchedule, IncomingMaterial, Supplier
from src.delivery.repository import DeliveryScheduleRepository
from src.waste.repository import WasteRepository

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "scheduled": {"delivered", "cancelled"},
}


class DeliveryService:
    """Handles status transitions and auto WasteRecord creation."""

    def __init__(
        self,
        session: AsyncSession,
        schedule_repo: DeliveryScheduleRepository,
        waste_repo: WasteRepository,
    ):
        self.session = session
        self.schedule_repo = schedule_repo
        self.waste_repo = waste_repo
        self._activity = ActivityService(session)

    async def update_status(
        self,
        schedule_id: str,
        new_status: str,
        actual_weight: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Transition delivery schedule status with side effects.

        scheduled → delivered: auto-create WasteRecord
        scheduled → cancelled: no side effects
        delivered/cancelled → *: rejected (400)
        """
        uid = uuid.UUID(schedule_id) if isinstance(schedule_id, str) else schedule_id
        result = await self.session.execute(
            select(DeliverySchedule).where(DeliverySchedule.id == uid)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None

        old_status = schedule.status
        allowed = VALID_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{old_status}' to '{new_status}'. "
                f"Allowed: {allowed or 'none (terminal state)'}"
            )

        if new_status == "delivered":
            waste_record = await self._create_waste_record(schedule, actual_weight)
            schedule.status = "delivered"
            schedule.actual_weight = actual_weight or schedule.estimated_weight
            if waste_record and waste_record.get("id"):
                schedule.waste_record_id = uuid.UUID(waste_record["id"])
            await self.session.commit()
            await self.session.refresh(schedule)

            await self._activity.log_delivery_event(
                action="delivered",
                schedule_id=str(schedule.id),
                title="搬入完了",
                description=f"重量: {schedule.actual_weight}{schedule.weight_unit}",
                metadata={"actual_weight": schedule.actual_weight},
            )

            return await self.schedule_repo.get_by_id(str(schedule.id))

        # cancelled
        schedule.status = "cancelled"
        await self.session.commit()
        await self.session.refresh(schedule)

        await self._activity.log_delivery_event(
            action="cancelled",
            schedule_id=str(schedule.id),
            title="搬入予定キャンセル",
            severity="warning",
        )

        return await self.schedule_repo.get_by_id(str(schedule.id))

    async def _create_waste_record(
        self,
        schedule: DeliverySchedule,
        actual_weight: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Create a WasteRecord from the delivery schedule data."""
        # Fetch incoming material + supplier
        mat_result = await self.session.execute(
            select(IncomingMaterial).where(
                IncomingMaterial.id == schedule.incoming_material_id
            )
        )
        material = mat_result.scalar_one_or_none()
        if not material:
            logger.error(f"IncomingMaterial {schedule.incoming_material_id} not found")
            return None

        sup_result = await self.session.execute(
            select(Supplier.name).where(Supplier.id == material.supplier_id)
        )
        supplier_name = sup_result.scalar_one_or_none() or "不明"

        weight = actual_weight or schedule.estimated_weight

        waste_data = {
            "source": supplier_name,
            "deliveryDate": schedule.scheduled_date.strftime("%Y-%m-%d"),
            "wasteType": material.material_category,
            "weight": weight,
            "weightUnit": schedule.weight_unit,
            "status": "pending",
            "notes": f"搬入予定より自動登録 (搬入物: {material.name})",
        }

        return await self.waste_repo.create(waste_data)
