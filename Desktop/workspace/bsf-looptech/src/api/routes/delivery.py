"""
API routes for incoming materials (搬入物マスター) and delivery schedules (搬入予定).
"""

import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.delivery.repository import (
    IncomingMaterialRepository,
    DeliveryScheduleRepository,
)
from src.delivery.schemas import (
    IncomingMaterialCreate,
    IncomingMaterialUpdate,
    IncomingMaterialResponse,
    DeliveryScheduleCreate,
    DeliveryScheduleUpdate,
    DeliveryScheduleResponse,
    StatusUpdateRequest,
)
from src.delivery.service import DeliveryService
from src.materials.schemas import PaginatedResponse, ImportResult
from src.waste.repository import WasteRepository

router = APIRouter(prefix="/api/v1", tags=["delivery"])

MAX_CSV_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Dependencies ──

async def get_material_repo(session: AsyncSession = Depends(get_async_session)):
    return IncomingMaterialRepository(session)


async def get_schedule_repo(session: AsyncSession = Depends(get_async_session)):
    return DeliveryScheduleRepository(session)


async def get_delivery_service(session: AsyncSession = Depends(get_async_session)):
    return DeliveryService(
        session=session,
        schedule_repo=DeliveryScheduleRepository(session),
        waste_repo=WasteRepository(session),
    )


# ── CSV helpers (reuse pattern from materials.py) ──

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


# ══════════════════════════════════════════════
#  Incoming Materials（搬入物マスター）
# ══════════════════════════════════════════════

@router.get(
    "/incoming-materials/export/csv",
    summary="搬入物マスターCSVエクスポート",
)
async def export_incoming_materials_csv(
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    items, _ = await repo.get_all(limit=10000, offset=0)
    columns = [
        "id", "supplier_id", "supplier_name", "material_category",
        "name", "description", "default_weight_unit", "notes", "is_active",
    ]
    buf = _dicts_to_csv(items, columns)
    return _csv_response(buf, "incoming_materials.csv")


@router.post(
    "/incoming-materials/import/csv",
    summary="搬入物マスターCSVインポート",
    response_model=ImportResult,
)
async def import_incoming_materials_csv(
    file: UploadFile = File(...),
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    raw = await file.read()
    if len(raw) > MAX_CSV_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")
    content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported, skipped, errors = 0, 0, []
    required = ["supplier_id", "material_category", "name"]
    for i, row in enumerate(reader, start=2):
        missing = [f for f in required if not row.get(f, "").strip()]
        if missing:
            skipped += 1
            errors.append(f"Row {i}: {', '.join(missing)} required")
            continue
        try:
            data = {
                "supplier_id": uuid.UUID(row["supplier_id"].strip()),
                "material_category": row["material_category"].strip(),
                "name": row["name"].strip(),
                "description": row.get("description", "").strip() or None,
                "default_weight_unit": row.get("default_weight_unit", "").strip() or "t",
                "notes": row.get("notes", "").strip() or None,
                "is_active": row.get("is_active", "true").strip().lower() != "false",
            }
            await repo.create(data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {str(e)[:100]}")
    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}


@router.get(
    "/incoming-materials/categories/{supplier_id}",
    summary="業者別カテゴリ一覧",
    response_model=list[str],
)
async def get_categories_by_supplier(
    supplier_id: str,
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    return await repo.get_categories_by_supplier(supplier_id)


@router.get(
    "/incoming-materials/by-supplier/{supplier_id}",
    summary="業者別搬入物一覧",
    response_model=list[IncomingMaterialResponse],
)
async def get_materials_by_supplier(
    supplier_id: str,
    category: Optional[str] = Query(None),
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    return await repo.get_by_supplier_and_category(supplier_id, category)


@router.post(
    "/incoming-materials",
    status_code=201,
    response_model=IncomingMaterialResponse,
)
async def create_incoming_material(
    body: IncomingMaterialCreate,
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    data = body.model_dump()
    data["supplier_id"] = str(data["supplier_id"])
    result = await repo.create(data)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create incoming material")
    # Return enriched result with supplier_name
    return await repo.get_by_id(result["id"])


@router.get(
    "/incoming-materials",
    summary="搬入物マスター一覧",
    response_model=PaginatedResponse[IncomingMaterialResponse],
)
async def list_incoming_materials(
    q: Optional[str] = Query(None, max_length=200),
    supplier_id: Optional[str] = Query(None),
    material_category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    items, total = await repo.get_all(
        q=q, supplier_id=supplier_id, material_category=material_category,
        is_active=is_active, sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/incoming-materials/{item_id}",
    response_model=IncomingMaterialResponse,
)
async def get_incoming_material(
    item_id: str,
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    result = await repo.get_by_id(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Incoming material not found")
    return result


@router.put(
    "/incoming-materials/{item_id}",
    response_model=IncomingMaterialResponse,
)
async def update_incoming_material(
    item_id: str,
    body: IncomingMaterialUpdate,
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    data = body.model_dump(exclude_unset=True)
    if "supplier_id" in data and data["supplier_id"] is not None:
        data["supplier_id"] = str(data["supplier_id"])
    result = await repo.update(item_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Incoming material not found")
    return result


@router.delete("/incoming-materials/{item_id}", status_code=204)
async def delete_incoming_material(
    item_id: str,
    repo: IncomingMaterialRepository = Depends(get_material_repo),
):
    deleted = await repo.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Incoming material not found")


# ══════════════════════════════════════════════
#  Delivery Schedules（搬入予定）
# ══════════════════════════════════════════════

@router.get(
    "/delivery-schedules/export/csv",
    summary="搬入予定CSVエクスポート",
)
async def export_delivery_schedules_csv(
    status: Optional[str] = Query(None),
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    items = await repo.get_all_for_export(status=status)
    columns = [
        "id", "incoming_material_id", "supplier_name", "material_category",
        "material_name", "scheduled_date", "estimated_weight", "actual_weight",
        "weight_unit", "status", "waste_record_id", "notes",
    ]
    buf = _dicts_to_csv(items, columns)
    return _csv_response(buf, "delivery_schedules.csv")


@router.post(
    "/delivery-schedules",
    status_code=201,
    response_model=DeliveryScheduleResponse,
)
async def create_delivery_schedule(
    body: DeliveryScheduleCreate,
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    data = body.model_dump()
    data["incoming_material_id"] = str(data["incoming_material_id"])
    result = await repo.create(data)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create delivery schedule")
    return result


@router.get(
    "/delivery-schedules",
    summary="搬入予定一覧",
    response_model=PaginatedResponse[DeliveryScheduleResponse],
)
async def list_delivery_schedules(
    q: Optional[str] = Query(None, max_length=200),
    status: Optional[str] = Query(None),
    incoming_material_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="開始日 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="終了日 YYYY-MM-DD"),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=1550),
    offset: int = Query(0, ge=0),
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    items, total = await repo.get_all(
        q=q, status=status, incoming_material_id=incoming_material_id,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/delivery-schedules/{item_id}",
    response_model=DeliveryScheduleResponse,
)
async def get_delivery_schedule(
    item_id: str,
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    result = await repo.get_by_id(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")
    return result


@router.put(
    "/delivery-schedules/{item_id}",
    response_model=DeliveryScheduleResponse,
)
async def update_delivery_schedule(
    item_id: str,
    body: DeliveryScheduleUpdate,
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    data = body.model_dump(exclude_unset=True)
    if "incoming_material_id" in data and data["incoming_material_id"] is not None:
        data["incoming_material_id"] = str(data["incoming_material_id"])
    result = await repo.update(item_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")
    return result


@router.put(
    "/delivery-schedules/{item_id}/status",
    summary="ステータス変更（搬入済/キャンセル）",
    response_model=DeliveryScheduleResponse,
)
async def update_delivery_schedule_status(
    item_id: str,
    body: StatusUpdateRequest,
    service: DeliveryService = Depends(get_delivery_service),
):
    try:
        result = await service.update_status(
            schedule_id=item_id,
            new_status=body.status,
            actual_weight=body.actual_weight,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")
    return result


@router.delete("/delivery-schedules/{item_id}", status_code=204)
async def delete_delivery_schedule(
    item_id: str,
    repo: DeliveryScheduleRepository = Depends(get_schedule_repo),
):
    deleted = await repo.delete(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Delivery schedule not found")
