"""
API routes for waste treatment records and material types.
Provides RESTful endpoints aligned with the frontend data model.
"""

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.waste.repository import WasteRepository, MaterialTypeRepository
from src.waste.service import WasteService, MaterialTypeService
from src.waste.models import (
    WasteRecordCreate,
    WasteRecordUpdate,
    WasteRecordResponse,
    MaterialTypeCreate,
    MaterialTypeUpdate,
    MaterialTypeResponse,
    RecommendationRequest,
)
from src.materials.schemas import PaginatedResponse, ImportResult
from src.waste.recommender import recommend_formulation
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/waste", tags=["waste"])

MAX_CSV_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Dependencies ──

async def get_waste_service(session: AsyncSession = Depends(get_async_session)) -> WasteService:
    return WasteService(WasteRepository(session))


async def get_material_service(session: AsyncSession = Depends(get_async_session)) -> MaterialTypeService:
    return MaterialTypeService(MaterialTypeRepository(session))


# ── Waste Record endpoints ──

@router.post("/records", status_code=201)
async def create_waste_record(
    data: WasteRecordCreate,
    service: WasteService = Depends(get_waste_service),
):
    """Create a new waste record."""
    result = await service.create_record(data.dict())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create waste record")
    return result


@router.get("/records", response_model=PaginatedResponse[WasteRecordResponse])
async def get_waste_records(
    q: Optional[str] = Query(None, description="Search source, waste_type, notes"),
    status: Optional[str] = Query(None),
    wasteType: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None, description="Column to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: WasteService = Depends(get_waste_service),
):
    """Get waste records with search, filters, pagination, sorting."""
    items, total = await service.get_all_records(
        q=q, status=status, waste_type=wasteType, source=source,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/records/export/csv")
async def export_waste_records_csv(
    status: Optional[str] = Query(None),
    wasteType: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    service: WasteService = Depends(get_waste_service),
):
    """Export all waste records as BOM-prefixed UTF-8 CSV."""
    records = await service.get_all_for_export(
        status=status, waste_type=wasteType, source=source,
    )

    buf = io.StringIO()
    fieldnames = [
        "id", "source", "deliveryDate", "wasteType", "weight", "weightUnit",
        "status", "analysis", "formulation", "elutionResult", "notes",
        "created_at", "updated_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        row = {**record}
        for json_field in ("analysis", "formulation", "elutionResult"):
            val = row.get(json_field)
            if val is not None and not isinstance(val, str):
                row[json_field] = json.dumps(val, ensure_ascii=False)
        writer.writerow(row)

    bom = "\ufeff"
    content = bom + buf.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="waste_records.csv"'},
    )


@router.post("/records/import/csv", response_model=ImportResult)
async def import_waste_records_csv(
    file: UploadFile = File(...),
    service: WasteService = Depends(get_waste_service),
):
    """Import waste records from CSV file."""
    raw = await file.read()
    if len(raw) > MAX_CSV_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum is {MAX_CSV_UPLOAD_BYTES} bytes.")

    content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported, skipped, errors = 0, 0, []

    required_fields = ["source", "deliveryDate", "wasteType"]

    for i, row in enumerate(reader, start=2):
        missing = [f for f in required_fields if not row.get(f, "").strip()]
        if missing:
            skipped += 1
            fields_str = " and ".join(missing) if len(missing) <= 2 else ", ".join(missing)
            errors.append(f"Row {i}: {fields_str} {'is' if len(missing) == 1 else 'are'} required")
            continue
        try:
            data = {
                "source": row["source"].strip(),
                "deliveryDate": row["deliveryDate"].strip(),
                "wasteType": row["wasteType"].strip(),
                "weight": float(row["weight"]) if row.get("weight", "").strip() else None,
                "weightUnit": row.get("weightUnit", "t").strip() or "t",
                "status": row.get("status", "pending").strip() or "pending",
                "notes": row.get("notes", "").strip() or None,
            }
            # Parse JSON fields
            for json_field in ("analysis", "formulation", "elutionResult"):
                raw_val = row.get(json_field, "").strip()
                if raw_val:
                    data[json_field] = json.loads(raw_val)

            await service.create_record(data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {str(e)[:100]}")

    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}


@router.get("/records/{record_id}")
async def get_waste_record(
    record_id: str,
    service: WasteService = Depends(get_waste_service),
):
    """Get a waste record by ID."""
    result = await service.get_record(record_id)
    if not result:
        raise HTTPException(status_code=404, detail="Waste record not found")
    return result


@router.put("/records/{record_id}")
async def update_waste_record(
    record_id: str,
    data: WasteRecordUpdate,
    service: WasteService = Depends(get_waste_service),
):
    """Update a waste record."""
    result = await service.update_record(record_id, data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Waste record not found or update failed")
    return result


@router.delete("/records/{record_id}")
async def delete_waste_record(
    record_id: str,
    service: WasteService = Depends(get_waste_service),
):
    """Delete a waste record."""
    success = await service.delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Waste record not found")
    return {"message": "Waste record deleted"}


# ── AI Recommendation ──

@router.post("/recommend")
async def recommend(
    data: RecommendationRequest,
    service: WasteService = Depends(get_waste_service),
):
    """Get AI-recommended formulation based on waste analysis data."""
    if not data.analysis or not any(
        v is not None for v in data.analysis.values()
    ):
        raise HTTPException(status_code=400, detail="Analysis data is required")

    # Fetch past records as training history
    items, _ = await service.get_all_records(limit=500)

    result = recommend_formulation(
        analysis=data.analysis,
        waste_type=data.wasteType,
        history=items,
    )
    return result


# ── Material Type endpoints ──

@router.post("/materials", status_code=201)
async def create_material_type(
    data: MaterialTypeCreate,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Create a new material type."""
    result = await service.create_type(data.dict())
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create material type")
    return result


@router.get("/materials")
async def get_material_types(
    category: Optional[str] = Query(None),
    service: MaterialTypeService = Depends(get_material_service),
):
    """Get all material types, optionally filtered by category."""
    return await service.get_all_types(category=category)


@router.get("/materials/{type_id}")
async def get_material_type(
    type_id: str,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Get a material type by ID."""
    result = await service.get_type(type_id)
    if not result:
        raise HTTPException(status_code=404, detail="Material type not found")
    return result


@router.put("/materials/{type_id}")
async def update_material_type(
    type_id: str,
    data: MaterialTypeUpdate,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Update a material type."""
    result = await service.update_type(type_id, data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Material type not found or update failed")
    return result


@router.delete("/materials/{type_id}")
async def delete_material_type(
    type_id: str,
    service: MaterialTypeService = Depends(get_material_service),
):
    """Delete a material type."""
    success = await service.delete_type(type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Material type not found")
    return {"message": "Material type deleted"}
