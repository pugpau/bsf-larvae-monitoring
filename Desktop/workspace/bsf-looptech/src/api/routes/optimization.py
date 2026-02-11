"""Cost optimization API routes."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import (
    SolidificationMaterial,
    LeachingSuppressant,
    get_async_session,
)
from src.ml.schemas import OptimizationRequest, OptimizationResponse
from src.optimization.solver import FormulationOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["optimization"])


async def _fetch_solidifiers(
    session: AsyncSession,
    candidates: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch active solidification materials from DB."""
    query = select(SolidificationMaterial).where(
        SolidificationMaterial.is_active.is_(True)
    )
    if candidates:
        query = query.where(SolidificationMaterial.name.in_(candidates))
    result = await session.execute(query)
    rows = result.scalars().all()
    return [
        {
            "name": r.name,
            "material_type": r.material_type,
            "unit_cost": r.unit_cost,
            "min_addition_rate": r.min_addition_rate,
            "max_addition_rate": r.max_addition_rate,
            "unit": r.unit or "kg",
        }
        for r in rows
    ]


async def _fetch_suppressants(
    session: AsyncSession,
    candidates: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Fetch active leaching suppressants from DB."""
    query = select(LeachingSuppressant).where(
        LeachingSuppressant.is_active.is_(True)
    )
    if candidates:
        query = query.where(LeachingSuppressant.name.in_(candidates))
    result = await session.execute(query)
    rows = result.scalars().all()
    return [
        {
            "name": r.name,
            "suppressant_type": r.suppressant_type,
            "unit_cost": r.unit_cost,
            "min_addition_rate": r.min_addition_rate,
            "max_addition_rate": r.max_addition_rate,
            "unit": r.unit or "kg",
        }
        for r in rows
    ]


@router.post("/optimize/formulation", response_model=OptimizationResponse)
async def optimize_formulation(
    data: OptimizationRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Find minimum-cost formulation satisfying treatment constraints.

    Uses PuLP linear programming to minimize material cost while ensuring:
    - Sufficient solidifier for the waste severity
    - Sufficient suppressant for metals exceeding limits
    - Material addition rates within allowed ranges
    - Optional budget constraint
    """
    solidifiers = await _fetch_solidifiers(session, data.candidate_solidifiers)
    suppressants = await _fetch_suppressants(session, data.candidate_suppressants)

    optimizer = FormulationOptimizer()
    return optimizer.optimize(data, solidifiers, suppressants)
