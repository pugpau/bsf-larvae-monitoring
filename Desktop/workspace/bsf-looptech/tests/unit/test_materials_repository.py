"""Unit tests for Phase 2 materials repository (search, pagination, sorting, export)."""

import pytest

from src.materials.repository import (
    SupplierRepository,
    SolidificationMaterialRepository,
    LeachingSuppressantRepository,
    RecipeRepository,
)


# ══════════════════════════════════════
#  Helper — bulk seed data
# ══════════════════════════════════════

async def _seed_suppliers(session, count=5):
    """Create test suppliers and return list of dicts."""
    repo = SupplierRepository(session)
    items = []
    for i in range(count):
        item = await repo.create({
            "name": f"搬入先_{chr(65 + i)}",
            "contact_person": f"担当者_{chr(65 + i)}",
            "address": f"住所_{chr(65 + i)}",
            "waste_types": ["汚泥"] if i % 2 == 0 else ["焼却灰"],
            "is_active": i != count - 1,  # last one is inactive
        })
        items.append(item)
    return items


async def _seed_solidification_materials(session, count=5):
    repo = SolidificationMaterialRepository(session)
    types = ["cement", "calcium", "ite", "other"]
    items = []
    for i in range(count):
        item = await repo.create({
            "name": f"固化材_{chr(65 + i)}",
            "material_type": types[i % len(types)],
            "base_material": f"ベース_{chr(65 + i)}",
            "min_addition_rate": 1.0 + i,
            "max_addition_rate": 10.0 + i,
            "unit_cost": 100.0 * (i + 1),
            "notes": f"備考_{chr(65 + i)}" if i % 2 == 0 else None,
        })
        items.append(item)
    return items


async def _seed_leaching_suppressants(session, count=5):
    repo = LeachingSuppressantRepository(session)
    types = ["chelate", "sulfide", "phosphate", "other"]
    items = []
    for i in range(count):
        item = await repo.create({
            "name": f"抑制剤_{chr(65 + i)}",
            "suppressant_type": types[i % len(types)],
            "target_metals": ["Pb", "Cd"] if i % 2 == 0 else ["Hg"],
            "min_addition_rate": 0.5 + i * 0.5,
            "max_addition_rate": 3.0 + i * 0.5,
            "notes": f"ノート_{chr(65 + i)}" if i < 3 else None,
        })
        items.append(item)
    return items


async def _seed_recipes(session, count=5):
    repo = RecipeRepository(session)
    statuses = ["draft", "active", "archived"]
    items = []
    for i in range(count):
        item = await repo.create({
            "name": f"レシピ_{chr(65 + i)}",
            "waste_type": "汚泥" if i % 2 == 0 else "焼却灰",
            "target_strength": 500.0 + i * 100,
            "status": statuses[i % len(statuses)],
            "notes": f"レシピ備考_{chr(65 + i)}" if i < 3 else None,
        })
        items.append(item)
    return items


# ══════════════════════════════════════
#  Supplier Repository Tests
# ══════════════════════════════════════

class TestSupplierSearch:

    @pytest.mark.asyncio
    async def test_search_by_name(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(q="搬入先_A")
        assert total >= 1
        assert any("搬入先_A" in item["name"] for item in items)

    @pytest.mark.asyncio
    async def test_search_by_contact_person(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(q="担当者_B")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_by_address(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(q="住所_C")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, async_session):
        """ILIKE search should be case insensitive for ASCII."""
        repo = SupplierRepository(async_session)
        await repo.create({"name": "TestSupplier", "contact_person": "John"})
        items, total = await repo.get_all(q="testsupplier")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_partial_match(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(q="搬入先")
        assert total >= 5

    @pytest.mark.asyncio
    async def test_search_no_match(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(q="存在しないキーワード")
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_filter_is_active(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(is_active=False)
        assert total >= 1
        for item in items:
            assert item["is_active"] is False


class TestSupplierPagination:

    @pytest.mark.asyncio
    async def test_pagination_limit(self, async_session):
        await _seed_suppliers(async_session, count=10)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(limit=3, offset=0)
        assert len(items) == 3
        assert total >= 10

    @pytest.mark.asyncio
    async def test_pagination_offset(self, async_session):
        await _seed_suppliers(async_session, count=10)
        repo = SupplierRepository(async_session)
        page1, _ = await repo.get_all(limit=3, offset=0)
        page2, _ = await repo.get_all(limit=3, offset=3)
        page1_ids = {item["id"] for item in page1}
        page2_ids = {item["id"] for item in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_pagination_offset_beyond_total(self, async_session):
        await _seed_suppliers(async_session, count=3)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(limit=10, offset=1000)
        assert items == []
        assert total >= 3

    @pytest.mark.asyncio
    async def test_total_count_reflects_filters(self, async_session):
        """Total should count only filtered results."""
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        _, total_all = await repo.get_all()
        _, total_search = await repo.get_all(q="搬入先_A")
        assert total_search <= total_all


class TestSupplierSorting:

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, _ = await repo.get_all(sort_by="name", sort_order="asc")
        names = [item["name"] for item in items]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_sort_by_name_desc(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, _ = await repo.get_all(sort_by="name", sort_order="desc")
        names = [item["name"] for item in items]
        assert names == sorted(names, reverse=True)

    @pytest.mark.asyncio
    async def test_sort_invalid_column_falls_back_to_created_at(self, async_session):
        """Invalid sort_by should not raise; falls back to created_at."""
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items, total = await repo.get_all(sort_by="nonexistent_column")
        assert total >= 5
        assert len(items) >= 5


class TestSupplierExport:

    @pytest.mark.asyncio
    async def test_export_returns_all(self, async_session):
        await _seed_suppliers(async_session, count=10)
        repo = SupplierRepository(async_session)
        items = await repo.get_all_for_export()
        assert len(items) >= 10

    @pytest.mark.asyncio
    async def test_export_with_filter(self, async_session):
        await _seed_suppliers(async_session)
        repo = SupplierRepository(async_session)
        items = await repo.get_all_for_export(is_active=False)
        for item in items:
            assert item["is_active"] is False


# ══════════════════════════════════════
#  Solidification Material Repository Tests
# ══════════════════════════════════════

class TestSolidificationMaterialSearch:

    @pytest.mark.asyncio
    async def test_search_by_name(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(q="固化材_A")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_by_base_material(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(q="ベース_B")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_by_notes(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(q="備考_A")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_filter_by_material_type(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(material_type="cement")
        assert total >= 1
        for item in items:
            assert item["material_type"] == "cement"

    @pytest.mark.asyncio
    async def test_combined_search_and_filter(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(q="固化材", material_type="cement")
        for item in items:
            assert item["material_type"] == "cement"
            assert "固化材" in item["name"]


class TestSolidificationMaterialPagination:

    @pytest.mark.asyncio
    async def test_pagination(self, async_session):
        await _seed_solidification_materials(async_session, count=8)
        repo = SolidificationMaterialRepository(async_session)
        items, total = await repo.get_all(limit=3, offset=0)
        assert len(items) == 3
        assert total >= 8


class TestSolidificationMaterialExport:

    @pytest.mark.asyncio
    async def test_export_all(self, async_session):
        await _seed_solidification_materials(async_session, count=5)
        repo = SolidificationMaterialRepository(async_session)
        items = await repo.get_all_for_export()
        assert len(items) >= 5

    @pytest.mark.asyncio
    async def test_export_with_type_filter(self, async_session):
        await _seed_solidification_materials(async_session)
        repo = SolidificationMaterialRepository(async_session)
        items = await repo.get_all_for_export(material_type="cement")
        for item in items:
            assert item["material_type"] == "cement"


# ══════════════════════════════════════
#  Leaching Suppressant Repository Tests
# ══════════════════════════════════════

class TestLeachingSuppressantSearch:

    @pytest.mark.asyncio
    async def test_search_by_name(self, async_session):
        await _seed_leaching_suppressants(async_session)
        repo = LeachingSuppressantRepository(async_session)
        items, total = await repo.get_all(q="抑制剤_A")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_by_notes(self, async_session):
        await _seed_leaching_suppressants(async_session)
        repo = LeachingSuppressantRepository(async_session)
        items, total = await repo.get_all(q="ノート_B")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_filter_by_suppressant_type(self, async_session):
        await _seed_leaching_suppressants(async_session)
        repo = LeachingSuppressantRepository(async_session)
        items, total = await repo.get_all(suppressant_type="chelate")
        assert total >= 1
        for item in items:
            assert item["suppressant_type"] == "chelate"


class TestLeachingSuppressantExport:

    @pytest.mark.asyncio
    async def test_export_all(self, async_session):
        await _seed_leaching_suppressants(async_session, count=5)
        repo = LeachingSuppressantRepository(async_session)
        items = await repo.get_all_for_export()
        assert len(items) >= 5


# ══════════════════════════════════════
#  Recipe Repository Tests
# ══════════════════════════════════════

class TestRecipeSearch:

    @pytest.mark.asyncio
    async def test_search_by_name(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(q="レシピ_A")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_search_by_notes(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(q="レシピ備考_B")
        assert total >= 1

    @pytest.mark.asyncio
    async def test_filter_by_waste_type(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(waste_type="汚泥")
        assert total >= 1
        for item in items:
            assert item["waste_type"] == "汚泥"

    @pytest.mark.asyncio
    async def test_filter_by_status(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(status="active")
        assert total >= 1
        for item in items:
            assert item["status"] == "active"

    @pytest.mark.asyncio
    async def test_combined_filters(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(waste_type="汚泥", status="draft")
        for item in items:
            assert item["waste_type"] == "汚泥"
            assert item["status"] == "draft"


class TestRecipePagination:

    @pytest.mark.asyncio
    async def test_pagination(self, async_session):
        await _seed_recipes(async_session, count=8)
        repo = RecipeRepository(async_session)
        items, total = await repo.get_all(limit=3, offset=0)
        assert len(items) == 3
        assert total >= 8

    @pytest.mark.asyncio
    async def test_pages_are_disjoint(self, async_session):
        await _seed_recipes(async_session, count=8)
        repo = RecipeRepository(async_session)
        page1, _ = await repo.get_all(limit=4, offset=0)
        page2, _ = await repo.get_all(limit=4, offset=4)
        ids1 = {item["id"] for item in page1}
        ids2 = {item["id"] for item in page2}
        assert ids1.isdisjoint(ids2)


class TestRecipeSorting:

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items, _ = await repo.get_all(sort_by="name", sort_order="asc")
        names = [item["name"] for item in items]
        assert names == sorted(names)


class TestRecipeExport:

    @pytest.mark.asyncio
    async def test_export_all(self, async_session):
        await _seed_recipes(async_session, count=5)
        repo = RecipeRepository(async_session)
        items = await repo.get_all_for_export()
        assert len(items) >= 5

    @pytest.mark.asyncio
    async def test_export_with_status_filter(self, async_session):
        await _seed_recipes(async_session)
        repo = RecipeRepository(async_session)
        items = await repo.get_all_for_export(status="draft")
        for item in items:
            assert item["status"] == "draft"

    @pytest.mark.asyncio
    async def test_export_includes_details(self, async_session):
        repo = RecipeRepository(async_session)
        item = await repo.create({
            "name": "エクスポートテスト",
            "waste_type": "汚泥",
            "status": "draft",
        })
        items = await repo.get_all_for_export()
        exported = next(i for i in items if i["id"] == item["id"])
        assert "details" in exported
