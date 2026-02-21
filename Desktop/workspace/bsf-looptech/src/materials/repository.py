"""Repository layer for Phase 1/2 material/supplier entities."""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgresql import (
    Supplier,
    SolidificationMaterial,
    LeachingSuppressant,
    Recipe,
    RecipeDetail,
    RecipeVersion,
    RecipeVersionDetail,
)

logger = logging.getLogger(__name__)


class _BaseRepository:
    """Generic CRUD repository with search, pagination, and sorting."""

    # Subclasses override to specify which columns are text-searchable
    _search_columns: list[str] = ["name"]
    # Subclasses override to specify which columns are valid for sorting
    _sortable_columns: list[str] = ["name", "created_at", "updated_at"]

    def __init__(self, session: AsyncSession, model_class):
        self.session = session
        self.model_class = model_class

    async def create(self, data: dict) -> dict:
        obj = self.model_class(id=uuid.uuid4(), **data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return self._to_dict(obj)

    async def get_by_id(self, item_id: str) -> Optional[dict]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == uid)
        )
        obj = result.scalar_one_or_none()
        return self._to_dict(obj) if obj else None

    async def get_all(
        self,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
        **filters,
    ) -> tuple[list[dict], int]:
        """Get all items with search, filters, pagination, sorting.

        Returns (items, total_count).
        """
        stmt = select(self.model_class)
        count_stmt = select(func.count()).select_from(self.model_class)

        # Apply exact-match filters
        for key, value in filters.items():
            if value is not None and hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)
                count_stmt = count_stmt.where(getattr(self.model_class, key) == value)

        # Apply text search (ILIKE across searchable columns)
        if q:
            pattern = f"%{q}%"
            conditions = []
            for col_name in self._search_columns:
                col = getattr(self.model_class, col_name, None)
                if col is not None:
                    conditions.append(col.ilike(pattern))
            if conditions:
                search_filter = or_(*conditions)
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)

        # Total count (before pagination)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting (only allow columns in the allowlist)
        sort_col = None
        if sort_by and sort_by in self._sortable_columns and hasattr(self.model_class, sort_by):
            sort_col = getattr(self.model_class, sort_by)
        if sort_col is None:
            sort_col = self.model_class.created_at
        stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        items = [self._to_dict(obj) for obj in result.scalars().all()]
        return items, total

    async def update(self, item_id: str, data: dict) -> Optional[dict]:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        clean = {k: v for k, v in data.items() if v is not None}
        if not clean:
            return await self.get_by_id(item_id)
        stmt = (
            update(self.model_class)
            .where(self.model_class.id == uid)
            .values(**clean)
            .returning(self.model_class)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        obj = result.scalar_one_or_none()
        return self._to_dict(obj) if obj else None

    async def delete(self, item_id: str) -> bool:
        uid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        stmt = delete(self.model_class).where(self.model_class.id == uid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_all_for_export(self, **filters) -> list[dict]:
        """Get all items without pagination (for CSV/Excel export)."""
        stmt = select(self.model_class)
        for key, value in filters.items():
            if value is not None and hasattr(self.model_class, key):
                stmt = stmt.where(getattr(self.model_class, key) == value)
        stmt = stmt.order_by(self.model_class.created_at.desc()).limit(50000)
        result = await self.session.execute(stmt)
        return [self._to_dict(obj) for obj in result.scalars().all()]

    def _to_dict(self, obj) -> dict:
        return {
            c.name: getattr(obj, c.name)
            for c in obj.__table__.columns
        }


class SupplierRepository(_BaseRepository):
    _search_columns = ["name", "contact_person", "address"]
    _sortable_columns = ["name", "contact_person", "is_active", "created_at", "updated_at"]

    def __init__(self, session: AsyncSession):
        super().__init__(session, Supplier)

    async def get_all(
        self,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
        **filters,
    ) -> tuple[list[dict], int]:
        if is_active is not None:
            filters["is_active"] = is_active
        return await super().get_all(
            q=q, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset, **filters,
        )


class SolidificationMaterialRepository(_BaseRepository):
    _search_columns = ["name", "base_material", "notes"]
    _sortable_columns = ["name", "material_type", "unit_cost", "is_active", "created_at", "updated_at"]

    def __init__(self, session: AsyncSession):
        super().__init__(session, SolidificationMaterial)

    async def get_all(
        self,
        material_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
        **filters,
    ) -> tuple[list[dict], int]:
        if material_type is not None:
            filters["material_type"] = material_type
        if is_active is not None:
            filters["is_active"] = is_active
        return await super().get_all(
            q=q, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset, **filters,
        )


class LeachingSuppressantRepository(_BaseRepository):
    _search_columns = ["name", "notes"]
    _sortable_columns = ["name", "suppressant_type", "unit_cost", "is_active", "created_at", "updated_at"]

    def __init__(self, session: AsyncSession):
        super().__init__(session, LeachingSuppressant)

    async def get_all(
        self,
        suppressant_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
        **filters,
    ) -> tuple[list[dict], int]:
        if suppressant_type is not None:
            filters["suppressant_type"] = suppressant_type
        if is_active is not None:
            filters["is_active"] = is_active
        return await super().get_all(
            q=q, sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset, **filters,
        )


class RecipeRepository:
    """Recipe repository with nested detail handling."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> dict:
        details_data = data.pop("details", [])
        recipe = Recipe(id=uuid.uuid4(), **data)
        self.session.add(recipe)
        await self.session.flush()

        for idx, detail in enumerate(details_data):
            detail_obj = RecipeDetail(
                id=uuid.uuid4(),
                recipe_id=recipe.id,
                order_index=detail.get("order_index", idx),
                material_id=detail["material_id"],
                material_type=detail["material_type"],
                addition_rate=detail["addition_rate"],
                notes=detail.get("notes"),
            )
            self.session.add(detail_obj)

        await self.session.commit()
        return await self.get_by_id(str(recipe.id))

    async def get_by_id(self, recipe_id: str) -> Optional[dict]:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        result = await self.session.execute(
            select(Recipe).where(Recipe.id == uid).options(selectinload(Recipe.details))
        )
        recipe = result.scalar_one_or_none()
        if not recipe:
            return None
        return self._to_dict(recipe)

    async def get_all(
        self,
        waste_type: Optional[str] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        stmt = select(Recipe).options(selectinload(Recipe.details))
        count_stmt = select(func.count()).select_from(Recipe)

        if waste_type is not None:
            stmt = stmt.where(Recipe.waste_type == waste_type)
            count_stmt = count_stmt.where(Recipe.waste_type == waste_type)
        if status is not None:
            stmt = stmt.where(Recipe.status == status)
            count_stmt = count_stmt.where(Recipe.status == status)

        # Text search
        if q:
            pattern = f"%{q}%"
            search_filter = or_(Recipe.name.ilike(pattern), Recipe.notes.ilike(pattern))
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Total count
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting (allowlist for safety)
        _recipe_sortable = {"name", "waste_type", "status", "created_at", "updated_at"}
        sort_col = None
        if sort_by and sort_by in _recipe_sortable and hasattr(Recipe, sort_by):
            sort_col = getattr(Recipe, sort_by)
        if sort_col is None:
            sort_col = Recipe.created_at
        stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        items = [self._to_dict(r) for r in result.scalars().all()]
        return items, total

    async def update(
        self,
        recipe_id: str,
        data: dict,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> Optional[dict]:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        change_summary = data.get("change_summary")
        clean = {k: v for k, v in data.items() if v is not None and k != "change_summary"}
        if not clean:
            return await self.get_by_id(recipe_id)

        # Lock row to prevent concurrent version conflicts (PostgreSQL only)
        lock_result = await self.session.execute(
            select(Recipe)
            .where(Recipe.id == uid)
            .with_for_update()
            .options(selectinload(Recipe.details))
        )
        recipe_obj = lock_result.scalar_one_or_none()
        if not recipe_obj:
            return None

        current = self._to_dict(recipe_obj)

        # Check if there's an actual change
        has_change = any(
            clean.get(k) != current.get(k) for k in clean if k in current
        )
        if has_change:
            await self._snapshot_current_version(
                current, change_summary, created_by=created_by,
            )
            clean["current_version"] = current["current_version"] + 1

        stmt = (
            update(Recipe)
            .where(Recipe.id == uid)
            .values(**clean)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(recipe_id)

    async def delete(self, recipe_id: str) -> bool:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        stmt = delete(Recipe).where(Recipe.id == uid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def add_detail(
        self,
        recipe_id: str,
        detail_data: dict,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> Optional[dict]:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id

        # Lock row for version safety
        lock_result = await self.session.execute(
            select(Recipe)
            .where(Recipe.id == uid)
            .with_for_update()
            .options(selectinload(Recipe.details))
        )
        recipe_obj = lock_result.scalar_one_or_none()
        if not recipe_obj:
            return None

        current = self._to_dict(recipe_obj)

        # Snapshot current state before adding detail
        mat_type = detail_data.get("material_type", "")
        await self._snapshot_current_version(
            current,
            f"明細追加: {mat_type}",
            created_by=created_by,
        )
        new_version = current["current_version"] + 1
        await self.session.execute(
            update(Recipe).where(Recipe.id == uid).values(current_version=new_version)
        )

        detail = RecipeDetail(
            id=uuid.uuid4(),
            recipe_id=uid,
            **detail_data,
        )
        self.session.add(detail)
        await self.session.commit()
        # Expire cached recipe so get_by_id reloads updated details
        self.session.expire(recipe_obj)
        return await self.get_by_id(recipe_id)

    async def remove_detail(
        self,
        recipe_id: str,
        detail_id: str,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> bool:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        detail_uid = uuid.UUID(detail_id) if isinstance(detail_id, str) else detail_id

        # Lock recipe row for version safety
        lock_result = await self.session.execute(
            select(Recipe)
            .where(Recipe.id == uid)
            .with_for_update()
            .options(selectinload(Recipe.details))
        )
        recipe_obj = lock_result.scalar_one_or_none()
        if not recipe_obj:
            return False

        # Verify detail belongs to this recipe BEFORE snapshotting
        detail_check = await self.session.execute(
            select(RecipeDetail.id).where(
                RecipeDetail.id == detail_uid,
                RecipeDetail.recipe_id == uid,
            )
        )
        if detail_check.scalar_one_or_none() is None:
            return False

        current = self._to_dict(recipe_obj)

        # Snapshot current state before removing detail
        await self._snapshot_current_version(
            current, "明細削除", created_by=created_by,
        )
        new_version = current["current_version"] + 1
        await self.session.execute(
            update(Recipe).where(Recipe.id == uid).values(current_version=new_version)
        )

        await self.session.execute(
            delete(RecipeDetail).where(
                RecipeDetail.id == detail_uid,
                RecipeDetail.recipe_id == uid,
            )
        )
        await self.session.commit()
        return True

    async def get_all_for_export(
        self,
        waste_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Get all recipes without pagination (for export)."""
        stmt = select(Recipe).options(selectinload(Recipe.details))
        if waste_type is not None:
            stmt = stmt.where(Recipe.waste_type == waste_type)
        if status is not None:
            stmt = stmt.where(Recipe.status == status)
        stmt = stmt.order_by(Recipe.created_at.desc()).limit(50000)
        result = await self.session.execute(stmt)
        return [self._to_dict(r) for r in result.scalars().all()]

    # ── Version Management ──

    _MAX_SUMMARY_LEN = 500

    async def _snapshot_current_version(
        self,
        recipe_dict: dict,
        change_summary: Optional[str] = None,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> None:
        """Save the current recipe state as a version snapshot."""
        if change_summary and len(change_summary) > self._MAX_SUMMARY_LEN:
            change_summary = change_summary[:self._MAX_SUMMARY_LEN]
        version = RecipeVersion(
            id=uuid.uuid4(),
            recipe_id=recipe_dict["id"],
            version=recipe_dict["current_version"],
            name=recipe_dict["name"],
            supplier_id=recipe_dict.get("supplier_id"),
            waste_type=recipe_dict["waste_type"],
            target_strength=recipe_dict.get("target_strength"),
            target_elution=recipe_dict.get("target_elution"),
            status=recipe_dict["status"],
            notes=recipe_dict.get("notes"),
            change_summary=change_summary,
            created_by=created_by,
        )
        self.session.add(version)
        await self.session.flush()

        for det in recipe_dict.get("details", []):
            vd = RecipeVersionDetail(
                id=uuid.uuid4(),
                version_id=version.id,
                material_id=det["material_id"],
                material_type=det["material_type"],
                addition_rate=det["addition_rate"],
                order_index=det.get("order_index", 0),
                notes=det.get("notes"),
            )
            self.session.add(vd)

    async def get_versions(self, recipe_id: str) -> list[dict]:
        """Get version history for a recipe (descending, max 100)."""
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        stmt = (
            select(RecipeVersion)
            .where(RecipeVersion.recipe_id == uid)
            .order_by(RecipeVersion.version.desc())
            .limit(100)
        )
        result = await self.session.execute(stmt)
        return [
            {c.name: getattr(v, c.name) for c in v.__table__.columns}
            for v in result.scalars().all()
        ]

    async def get_version(self, recipe_id: str, version: int) -> Optional[dict]:
        """Get a specific version snapshot with details."""
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        stmt = (
            select(RecipeVersion)
            .where(RecipeVersion.recipe_id == uid, RecipeVersion.version == version)
            .options(selectinload(RecipeVersion.details))
        )
        result = await self.session.execute(stmt)
        v = result.scalar_one_or_none()
        if not v:
            return None
        d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
        d["details"] = [
            {c.name: getattr(det, c.name) for c in det.__table__.columns}
            for det in v.details
        ]
        return d

    async def rollback_to_version(
        self,
        recipe_id: str,
        version: int,
        *,
        created_by: Optional[uuid.UUID] = None,
    ) -> Optional[dict]:
        """Rollback recipe to a specific version. Snapshots current state first."""
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id

        # Lock row and load current state atomically
        lock_result = await self.session.execute(
            select(Recipe)
            .where(Recipe.id == uid)
            .with_for_update()
            .options(selectinload(Recipe.details))
        )
        recipe_obj = lock_result.scalar_one_or_none()
        if not recipe_obj:
            return None

        # Load target version inside lock scope
        target = await self.get_version(recipe_id, version)
        if not target:
            return None

        current = self._to_dict(recipe_obj)

        # Snapshot current state before rollback
        await self._snapshot_current_version(
            current,
            f"Rolled back to version {version}",
            created_by=created_by,
        )
        new_version = current["current_version"] + 1

        # Update recipe header from target version
        stmt = (
            update(Recipe)
            .where(Recipe.id == uid)
            .values(
                name=target["name"],
                supplier_id=target.get("supplier_id"),
                waste_type=target["waste_type"],
                target_strength=target.get("target_strength"),
                target_elution=target.get("target_elution"),
                status=target["status"],
                notes=target.get("notes"),
                current_version=new_version,
            )
        )
        await self.session.execute(stmt)

        # Replace details: delete current, copy from target version
        await self.session.execute(
            delete(RecipeDetail).where(RecipeDetail.recipe_id == uid)
        )
        for det in target.get("details", []):
            self.session.add(RecipeDetail(
                id=uuid.uuid4(),
                recipe_id=uid,
                material_id=det["material_id"],
                material_type=det["material_type"],
                addition_rate=det["addition_rate"],
                order_index=det.get("order_index", 0),
                notes=det.get("notes"),
            ))

        await self.session.commit()
        self.session.expire(recipe_obj)
        return await self.get_by_id(recipe_id)

    def _compute_diff(
        self,
        old_dict: dict,
        new_dict: dict,
        recipe_id,
        version_from,
        version_to,
    ) -> dict:
        """Compute diff between two recipe states."""
        header_fields = [
            "name", "supplier_id", "waste_type", "target_strength",
            "target_elution", "status", "notes",
        ]
        header_changes = []
        for field in header_fields:
            old_val = old_dict.get(field)
            new_val = new_dict.get(field)
            if old_val != new_val:
                header_changes.append({
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val,
                })

        def _detail_key(d: dict) -> str:
            return f"{d['material_id']}:{d.get('order_index', 0)}"

        old_details = {_detail_key(d): d for d in old_dict.get("details", [])}
        new_details = {_detail_key(d): d for d in new_dict.get("details", [])}

        old_keys = set(old_details.keys())
        new_keys = set(new_details.keys())

        details_added = [new_details[k] for k in new_keys - old_keys]
        details_removed = [old_details[k] for k in old_keys - new_keys]

        details_modified = []
        for k in old_keys & new_keys:
            old_d = old_details[k]
            new_d = new_details[k]
            changes = {}
            for f in ("addition_rate", "order_index", "notes", "material_type"):
                if old_d.get(f) != new_d.get(f):
                    changes[f] = {"old": old_d.get(f), "new": new_d.get(f)}
            if changes:
                changes["material_id"] = k
                details_modified.append(changes)

        return {
            "recipe_id": recipe_id,
            "version_from": version_from,
            "version_to": version_to,
            "header_changes": header_changes,
            "details_added": details_added,
            "details_removed": details_removed,
            "details_modified": details_modified,
        }

    async def diff_versions(
        self, recipe_id: str, v1: int, v2: int
    ) -> Optional[dict]:
        """Compute diff between two versions."""
        ver1 = await self.get_version(recipe_id, v1)
        ver2 = await self.get_version(recipe_id, v2)
        if not ver1 or not ver2:
            return None

        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        return self._compute_diff(ver1, ver2, uid, v1, v2)

    async def diff_with_current(
        self, recipe_id: str, version: int
    ) -> Optional[dict]:
        """Compute diff between a stored version and the current live recipe."""
        ver = await self.get_version(recipe_id, version)
        if not ver:
            return None

        current = await self.get_by_id(recipe_id)
        if not current:
            return None

        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        return self._compute_diff(
            ver, current, uid, version, current["current_version"],
        )

    def _to_dict(self, recipe: Recipe) -> dict:
        d = {c.name: getattr(recipe, c.name) for c in recipe.__table__.columns}
        d["details"] = [
            {c.name: getattr(det, c.name) for c in det.__table__.columns}
            for det in recipe.details
        ]
        return d
