"""
API routes for formulation workflow (搬入→配合連携).
"""

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.formulation.repository import FormulationRecordRepository
from src.formulation.schemas import (
    FormulationRecordCreate,
    FormulationRecordResponse,
    FormulationRecordUpdate,
    RecommendRequest,
    RecommendResponse,
    StatusTransitionRequest,
)
from src.formulation.service import FormulationWorkflowService
from src.materials.schemas import PaginatedResponse

router = APIRouter(prefix="/api/v1/formulations", tags=["formulations"])


# ── CSV helpers ──

_CSV_COLUMNS = [
    "id", "waste_record_id", "waste_type", "waste_source",
    "source_type", "status", "recipe_name",
    "confidence", "estimated_cost", "actual_cost",
    "elution_passed", "planned_formulation", "actual_formulation",
    "elution_result", "reasoning", "notes",
    "created_at", "updated_at",
]


def _dicts_to_csv(rows: list[dict], columns: list[str]) -> io.StringIO:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for col in columns:
            val = row.get(col)
            if val is None:
                clean[col] = ""
            elif isinstance(val, (dict, list)):
                clean[col] = json.dumps(val, ensure_ascii=False)
            else:
                clean[col] = val
        writer.writerow(clean)
    buf.seek(0)
    return buf


def _csv_response(buf: io.StringIO, filename: str) -> StreamingResponse:
    bom = "\ufeff"
    content = bom + buf.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Dependencies ──

async def get_repo(session: AsyncSession = Depends(get_async_session)):
    return FormulationRecordRepository(session)


async def get_service(session: AsyncSession = Depends(get_async_session)):
    return FormulationWorkflowService(session)


# ── CSV export ──


@router.get(
    "/export/csv",
    summary="配合記録CSVエクスポート",
)
async def export_formulations_csv(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Export formulation records as BOM-prefixed UTF-8 CSV."""
    items, _ = await repo.get_all(
        status=status,
        source_type=source_type,
        limit=10000,
        offset=0,
    )
    buf = _dicts_to_csv(items, _CSV_COLUMNS)
    return _csv_response(buf, "formulations.csv")


# ── CRUD endpoints ──


@router.get("", response_model=PaginatedResponse)
async def list_formulations(
    waste_record_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """List formulation records with filters and pagination."""
    items, total = await repo.get_all(
        waste_record_id=waste_record_id,
        status=status,
        source_type=source_type,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/by-waste-record/{waste_record_id}")
async def get_by_waste_record(
    waste_record_id: str,
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Get all formulation records for a specific waste record."""
    items = await repo.get_by_waste_record(waste_record_id)
    return {"items": items, "total": len(items)}


@router.get("/{formulation_id}", response_model=FormulationRecordResponse)
async def get_formulation(
    formulation_id: str,
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Get a single formulation record by ID."""
    item = await repo.get_by_id(formulation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return item


@router.post("", response_model=FormulationRecordResponse, status_code=201)
async def create_formulation(
    body: FormulationRecordCreate,
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Create a manual formulation record."""
    data = body.model_dump(exclude_none=True)
    result = await repo.create(data)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create formulation record")
    return result


@router.put("/{formulation_id}", response_model=FormulationRecordResponse)
async def update_formulation(
    formulation_id: str,
    body: FormulationRecordUpdate,
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Update a formulation record (modifiable fields only)."""
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await repo.update(formulation_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return result


@router.delete("/{formulation_id}", status_code=204)
async def delete_formulation(
    formulation_id: str,
    repo: FormulationRecordRepository = Depends(get_repo),
):
    """Delete a formulation record (only proposed/rejected)."""
    try:
        deleted = await repo.delete(formulation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Formulation record not found")


# ── Workflow endpoints ──


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_formulations(
    body: RecommendRequest,
    service: FormulationWorkflowService = Depends(get_service),
):
    """Generate formulation candidates for a waste record (ML + optimization + recipe matching)."""
    try:
        candidates = await service.recommend(
            waste_record_id=str(body.waste_record_id),
            top_k=body.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    waste_type = candidates[0].get("waste_type") if candidates else None
    return {
        "candidates": candidates,
        "waste_record_id": body.waste_record_id,
        "waste_type": waste_type,
    }


@router.post("/{formulation_id}/accept", response_model=FormulationRecordResponse)
async def accept_formulation(
    formulation_id: str,
    service: FormulationWorkflowService = Depends(get_service),
):
    """Accept a proposed formulation (proposed → accepted)."""
    try:
        result = await service.accept(formulation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return result


@router.post("/{formulation_id}/apply", response_model=FormulationRecordResponse)
async def apply_formulation(
    formulation_id: str,
    body: Optional[StatusTransitionRequest] = None,
    service: FormulationWorkflowService = Depends(get_service),
):
    """Apply a formulation (accepted → applied). Updates WasteRecord."""
    actual_formulation = body.actual_formulation if body else None
    actual_cost = body.actual_cost if body else None
    try:
        result = await service.apply_formulation(
            formulation_id,
            actual_formulation=actual_formulation,
            actual_cost=actual_cost,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return result


@router.post("/{formulation_id}/verify", response_model=FormulationRecordResponse)
async def verify_formulation(
    formulation_id: str,
    body: StatusTransitionRequest,
    service: FormulationWorkflowService = Depends(get_service),
):
    """Verify with elution test results (applied → verified)."""
    if body.elution_result is None:
        raise HTTPException(status_code=400, detail="elution_result is required for verification")
    if body.elution_passed is None:
        raise HTTPException(status_code=400, detail="elution_passed is required for verification")
    try:
        result = await service.verify(
            formulation_id,
            elution_result=body.elution_result,
            elution_passed=body.elution_passed,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return result


@router.post("/{formulation_id}/reject", response_model=FormulationRecordResponse)
async def reject_formulation(
    formulation_id: str,
    body: Optional[StatusTransitionRequest] = None,
    service: FormulationWorkflowService = Depends(get_service),
):
    """Reject a formulation at any valid stage."""
    notes = body.notes if body else None
    try:
        result = await service.reject(formulation_id, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Formulation record not found")
    return result
