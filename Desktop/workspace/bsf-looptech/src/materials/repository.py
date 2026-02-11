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
)

logger = logging.getLogger(__name__)


class _BaseRepository:
    """Generic CRUD repository with search, pagination, and sorting."""

    # Subclasses override to specify which columns are text-searchable
    _search_columns: list[str] = ["name"]

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

        # Sorting
        sort_col = None
        if sort_by and hasattr(self.model_class, sort_by):
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
        stmt = stmt.order_by(self.model_class.created_at.desc())
        result = await self.session.execute(stmt)
        return [self._to_dict(obj) for obj in result.scalars().all()]

    def _to_dict(self, obj) -> dict:
        return {
            c.name: getattr(obj, c.name)
            for c in obj.__table__.columns
        }


class SupplierRepository(_BaseRepository):
    _search_columns = ["name", "contact_person", "address"]

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

        # Sorting
        sort_col = None
        if sort_by and hasattr(Recipe, sort_by):
            sort_col = getattr(Recipe, sort_by)
        if sort_col is None:
            sort_col = Recipe.created_at
        stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        items = [self._to_dict(r) for r in result.scalars().all()]
        return items, total

    async def update(self, recipe_id: str, data: dict) -> Optional[dict]:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        clean = {k: v for k, v in data.items() if v is not None}
        if not clean:
            return await self.get_by_id(recipe_id)
        stmt = (
            update(Recipe)
            .where(Recipe.id == uid)
            .values(**clean)
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            return None
        await self.session.commit()
        return await self.get_by_id(recipe_id)

    async def delete(self, recipe_id: str) -> bool:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        stmt = delete(Recipe).where(Recipe.id == uid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def add_detail(self, recipe_id: str, detail_data: dict) -> Optional[dict]:
        uid = uuid.UUID(recipe_id) if isinstance(recipe_id, str) else recipe_id
        recipe = await self.get_by_id(recipe_id)
        if not recipe:
            return None
        detail = RecipeDetail(
            id=uuid.uuid4(),
            recipe_id=uid,
            **detail_data,
        )
        self.session.add(detail)
        await self.session.commit()
        return await self.get_by_id(recipe_id)

    async def remove_detail(self, detail_id: str) -> bool:
        uid = uuid.UUID(detail_id) if isinstance(detail_id, str) else detail_id
        stmt = delete(RecipeDetail).where(RecipeDetail.id == uid)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

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
        stmt = stmt.order_by(Recipe.created_at.desc())
        result = await self.session.execute(stmt)
        return [self._to_dict(r) for r in result.scalars().all()]

    def _to_dict(self, recipe: Recipe) -> dict:
        d = {c.name: getattr(recipe, c.name) for c in recipe.__table__.columns}
        d["details"] = [
            {c.name: getattr(det, c.name) for c in det.__table__.columns}
            for det in recipe.details
        ]
        return d
