"""
API routes for Phase 1/2: suppliers, solidification materials, leaching suppressants, recipes.
Phase 2 additions: search, pagination, sorting, CSV export/import.
"""

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import get_async_session
from src.materials.repository import (
    SupplierRepository,
    SolidificationMaterialRepository,
    LeachingSuppressantRepository,
    RecipeRepository,
)
from src.materials.schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    SolidificationMaterialCreate, SolidificationMaterialUpdate, SolidificationMaterialResponse,
    LeachingSuppressantCreate, LeachingSuppressantUpdate, LeachingSuppressantResponse,
    RecipeCreate, RecipeUpdate, RecipeResponse,
    RecipeDetailCreate,
    PaginatedResponse,
    ImportResult,
)

router = APIRouter(prefix="/api/v1", tags=["materials"])


# ── Dependencies ──

async def get_supplier_repo(session: AsyncSession = Depends(get_async_session)):
    return SupplierRepository(session)

async def get_solidification_repo(session: AsyncSession = Depends(get_async_session)):
    return SolidificationMaterialRepository(session)

async def get_suppressant_repo(session: AsyncSession = Depends(get_async_session)):
    return LeachingSuppressantRepository(session)

async def get_recipe_repo(session: AsyncSession = Depends(get_async_session)):
    return RecipeRepository(session)


# ── CSV helpers ──

def _dicts_to_csv(rows: list[dict], columns: list[str]) -> io.StringIO:
    """Convert list of dicts to CSV StringIO, serializing complex types."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for col in columns:
            val = row.get(col)
            if isinstance(val, (dict, list)):
                clean[col] = json.dumps(val, ensure_ascii=False)
            elif val is None:
                clean[col] = ""
            else:
                clean[col] = val
        writer.writerow(clean)
    buf.seek(0)
    return buf


def _csv_response(buf: io.StringIO, filename: str) -> StreamingResponse:
    """Create a streaming CSV response with BOM for Excel compatibility."""
    bom = "\ufeff"
    content = bom + buf.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════
#  Suppliers（搬入先マスタ）
# ══════════════════════════════════════════════

@router.post("/suppliers", status_code=201, response_model=SupplierResponse)
async def create_supplier(
    data: SupplierCreate,
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    result = await repo.create(data.model_dump())
    return result


@router.get("/suppliers", response_model=PaginatedResponse[SupplierResponse])
async def get_suppliers(
    q: Optional[str] = Query(None, description="Search name, contact, address"),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None, description="Column to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    items, total = await repo.get_all(
        q=q, is_active=is_active,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/suppliers/export/csv")
async def export_suppliers_csv(
    is_active: Optional[bool] = Query(None),
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    rows = await repo.get_all_for_export(**filters)
    columns = ["id", "name", "contact_person", "phone", "email", "address", "waste_types", "notes", "is_active"]
    buf = _dicts_to_csv(rows, columns)
    return _csv_response(buf, "suppliers.csv")


@router.post("/suppliers/import/csv", response_model=ImportResult)
async def import_suppliers_csv(
    file: UploadFile = File(...),
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        if not name:
            skipped += 1
            errors.append(f"Row {i}: name is required")
            continue
        try:
            waste_types = json.loads(row.get("waste_types", "[]")) if row.get("waste_types") else []
            data = {
                "name": name,
                "contact_person": row.get("contact_person") or None,
                "phone": row.get("phone") or None,
                "email": row.get("email") or None,
                "address": row.get("address") or None,
                "waste_types": waste_types,
                "notes": row.get("notes") or None,
                "is_active": row.get("is_active", "true").lower() in ("true", "1", "yes"),
            }
            await repo.create(data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {str(e)[:100]}")
    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    result = await repo.get_by_id(supplier_id)
    if not result:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return result


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    result = await repo.update(supplier_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return result


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    repo: SupplierRepository = Depends(get_supplier_repo),
):
    if not await repo.delete(supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted"}


# ══════════════════════════════════════════════
#  Solidification Materials（固化材マスタ）
# ══════════════════════════════════════════════

@router.post("/solidification-materials", status_code=201, response_model=SolidificationMaterialResponse)
async def create_solidification_material(
    data: SolidificationMaterialCreate,
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    result = await repo.create(data.model_dump())
    return result


@router.get("/solidification-materials", response_model=PaginatedResponse[SolidificationMaterialResponse])
async def get_solidification_materials(
    q: Optional[str] = Query(None, description="Search name, base_material, notes"),
    material_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    items, total = await repo.get_all(
        q=q, material_type=material_type, is_active=is_active,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/solidification-materials/export/csv")
async def export_solidification_csv(
    material_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    filters = {}
    if material_type is not None:
        filters["material_type"] = material_type
    if is_active is not None:
        filters["is_active"] = is_active
    rows = await repo.get_all_for_export(**filters)
    columns = [
        "id", "name", "material_type", "base_material", "effective_components",
        "applicable_soil_types", "min_addition_rate", "max_addition_rate",
        "unit_cost", "unit", "notes", "is_active",
    ]
    buf = _dicts_to_csv(rows, columns)
    return _csv_response(buf, "solidification_materials.csv")


@router.post("/solidification-materials/import/csv", response_model=ImportResult)
async def import_solidification_csv(
    file: UploadFile = File(...),
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        material_type = row.get("material_type", "").strip()
        if not name or not material_type:
            skipped += 1
            errors.append(f"Row {i}: name and material_type are required")
            continue
        try:
            data = {
                "name": name,
                "material_type": material_type,
                "base_material": row.get("base_material") or None,
                "min_addition_rate": float(row["min_addition_rate"]) if row.get("min_addition_rate") else None,
                "max_addition_rate": float(row["max_addition_rate"]) if row.get("max_addition_rate") else None,
                "unit_cost": float(row["unit_cost"]) if row.get("unit_cost") else None,
                "unit": row.get("unit") or "kg",
                "notes": row.get("notes") or None,
                "is_active": row.get("is_active", "true").lower() in ("true", "1", "yes"),
            }
            await repo.create(data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {str(e)[:100]}")
    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}


@router.get("/solidification-materials/{item_id}", response_model=SolidificationMaterialResponse)
async def get_solidification_material(
    item_id: str,
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    result = await repo.get_by_id(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Solidification material not found")
    return result


@router.put("/solidification-materials/{item_id}", response_model=SolidificationMaterialResponse)
async def update_solidification_material(
    item_id: str,
    data: SolidificationMaterialUpdate,
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    result = await repo.update(item_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Solidification material not found")
    return result


@router.delete("/solidification-materials/{item_id}")
async def delete_solidification_material(
    item_id: str,
    repo: SolidificationMaterialRepository = Depends(get_solidification_repo),
):
    if not await repo.delete(item_id):
        raise HTTPException(status_code=404, detail="Solidification material not found")
    return {"message": "Solidification material deleted"}


# ══════════════════════════════════════════════
#  Leaching Suppressants（溶出抑制剤マスタ）
# ══════════════════════════════════════════════

@router.post("/leaching-suppressants", status_code=201, response_model=LeachingSuppressantResponse)
async def create_leaching_suppressant(
    data: LeachingSuppressantCreate,
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    result = await repo.create(data.model_dump())
    return result


@router.get("/leaching-suppressants", response_model=PaginatedResponse[LeachingSuppressantResponse])
async def get_leaching_suppressants(
    q: Optional[str] = Query(None, description="Search name, notes"),
    suppressant_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    items, total = await repo.get_all(
        q=q, suppressant_type=suppressant_type, is_active=is_active,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/leaching-suppressants/export/csv")
async def export_suppressants_csv(
    suppressant_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    filters = {}
    if suppressant_type is not None:
        filters["suppressant_type"] = suppressant_type
    if is_active is not None:
        filters["is_active"] = is_active
    rows = await repo.get_all_for_export(**filters)
    columns = [
        "id", "name", "suppressant_type", "target_metals",
        "min_addition_rate", "max_addition_rate",
        "ph_range_min", "ph_range_max",
        "unit_cost", "unit", "notes", "is_active",
    ]
    buf = _dicts_to_csv(rows, columns)
    return _csv_response(buf, "leaching_suppressants.csv")


@router.post("/leaching-suppressants/import/csv", response_model=ImportResult)
async def import_suppressants_csv(
    file: UploadFile = File(...),
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported, skipped, errors = 0, 0, []
    for i, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        suppressant_type = row.get("suppressant_type", "").strip()
        if not name or not suppressant_type:
            skipped += 1
            errors.append(f"Row {i}: name and suppressant_type are required")
            continue
        try:
            target_metals = json.loads(row.get("target_metals", "[]")) if row.get("target_metals") else []
            data = {
                "name": name,
                "suppressant_type": suppressant_type,
                "target_metals": target_metals,
                "min_addition_rate": float(row["min_addition_rate"]) if row.get("min_addition_rate") else None,
                "max_addition_rate": float(row["max_addition_rate"]) if row.get("max_addition_rate") else None,
                "ph_range_min": float(row["ph_range_min"]) if row.get("ph_range_min") else None,
                "ph_range_max": float(row["ph_range_max"]) if row.get("ph_range_max") else None,
                "unit_cost": float(row["unit_cost"]) if row.get("unit_cost") else None,
                "unit": row.get("unit") or "kg",
                "notes": row.get("notes") or None,
                "is_active": row.get("is_active", "true").lower() in ("true", "1", "yes"),
            }
            await repo.create(data)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {str(e)[:100]}")
    return {"imported": imported, "skipped": skipped, "errors": errors[:20]}


@router.get("/leaching-suppressants/{item_id}", response_model=LeachingSuppressantResponse)
async def get_leaching_suppressant(
    item_id: str,
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    result = await repo.get_by_id(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Leaching suppressant not found")
    return result


@router.put("/leaching-suppressants/{item_id}", response_model=LeachingSuppressantResponse)
async def update_leaching_suppressant(
    item_id: str,
    data: LeachingSuppressantUpdate,
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    result = await repo.update(item_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Leaching suppressant not found")
    return result


@router.delete("/leaching-suppressants/{item_id}")
async def delete_leaching_suppressant(
    item_id: str,
    repo: LeachingSuppressantRepository = Depends(get_suppressant_repo),
):
    if not await repo.delete(item_id):
        raise HTTPException(status_code=404, detail="Leaching suppressant not found")
    return {"message": "Leaching suppressant deleted"}


# ══════════════════════════════════════════════
#  Recipes（配合レシピ）
# ══════════════════════════════════════════════

@router.post("/recipes", status_code=201, response_model=RecipeResponse)
async def create_recipe(
    data: RecipeCreate,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    result = await repo.create(data.model_dump())
    return result


@router.get("/recipes", response_model=PaginatedResponse[RecipeResponse])
async def get_recipes(
    q: Optional[str] = Query(None, description="Search name, notes"),
    waste_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    items, total = await repo.get_all(
        q=q, waste_type=waste_type, status=status,
        sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/recipes/export/csv")
async def export_recipes_csv(
    waste_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    rows = await repo.get_all_for_export(waste_type=waste_type, status=status)
    columns = ["id", "name", "waste_type", "target_strength", "target_elution", "status", "notes"]
    buf = _dicts_to_csv(rows, columns)
    return _csv_response(buf, "recipes.csv")


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: str,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    result = await repo.get_by_id(recipe_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return result


@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
    recipe_id: str,
    data: RecipeUpdate,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    result = await repo.update(recipe_id, data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return result


@router.delete("/recipes/{recipe_id}")
async def delete_recipe(
    recipe_id: str,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    if not await repo.delete(recipe_id):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted"}


@router.post("/recipes/{recipe_id}/details", status_code=201, response_model=RecipeResponse)
async def add_recipe_detail(
    recipe_id: str,
    data: RecipeDetailCreate,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    result = await repo.add_detail(recipe_id, data.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return result


@router.delete("/recipes/{recipe_id}/details/{detail_id}")
async def remove_recipe_detail(
    recipe_id: str,
    detail_id: str,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
    if not await repo.remove_detail(detail_id):
        raise HTTPException(status_code=404, detail="Recipe detail not found")
    return {"message": "Recipe detail removed"}
