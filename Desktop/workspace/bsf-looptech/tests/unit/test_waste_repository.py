"""
Unit tests for waste repository and service classes.
Tests WasteRepository, MaterialTypeRepository, WasteService, MaterialTypeService.
"""

import pytest

from src.waste.repository import WasteRepository, MaterialTypeRepository
from src.waste.service import WasteService, MaterialTypeService


# ===========================================================================
# WasteRepository
# ===========================================================================


@pytest.mark.unit
class TestWasteRepositoryCreate:
    async def test_create_record(self, async_session):
        repo = WasteRepository(async_session)
        data = {
            "source": "工場A",
            "deliveryDate": "2026-01-15",
            "wasteType": "汚泥",
            "weight": 10.5,
            "weightUnit": "t",
            "status": "pending",
            "notes": "テスト搬入",
        }
        result = await repo.create(data)
        assert result is not None
        assert result["source"] == "工場A"
        assert result["wasteType"] == "汚泥"
        assert result["weight"] == 10.5
        assert result["status"] == "pending"
        assert result["id"] is not None

    async def test_create_record_with_analysis(self, async_session):
        repo = WasteRepository(async_session)
        data = {
            "source": "工場B",
            "deliveryDate": "2026-01-20",
            "wasteType": "焼却灰",
            "analysis": {"pH": 7.0, "Pb": 0.005},
        }
        result = await repo.create(data)
        assert result is not None
        assert result["analysis"]["pH"] == 7.0

    async def test_create_record_minimal(self, async_session):
        repo = WasteRepository(async_session)
        data = {
            "source": "工場C",
            "deliveryDate": "2026-02-01",
            "wasteType": "飛灰",
        }
        result = await repo.create(data)
        assert result is not None
        assert result["weightUnit"] == "t"
        assert result["status"] == "pending"


@pytest.mark.unit
class TestWasteRepositoryRead:
    async def test_get_all_empty(self, async_session):
        repo = WasteRepository(async_session)
        result = await repo.get_all()
        assert result == []

    async def test_get_all_with_records(self, async_session):
        repo = WasteRepository(async_session)
        for i in range(3):
            await repo.create({
                "source": f"src_{i}",
                "deliveryDate": f"2026-01-{10 + i:02d}",
                "wasteType": "汚泥",
            })
        result = await repo.get_all()
        assert len(result) == 3

    async def test_get_all_with_status_filter(self, async_session):
        repo = WasteRepository(async_session)
        await repo.create({
            "source": "A", "deliveryDate": "2026-01-10",
            "wasteType": "汚泥", "status": "pending",
        })
        await repo.create({
            "source": "B", "deliveryDate": "2026-01-11",
            "wasteType": "汚泥", "status": "analyzed",
        })
        result = await repo.get_all(status="pending")
        assert len(result) == 1
        assert result[0]["source"] == "A"

    async def test_get_all_with_waste_type_filter(self, async_session):
        repo = WasteRepository(async_session)
        await repo.create({
            "source": "A", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        await repo.create({
            "source": "B", "deliveryDate": "2026-01-11", "wasteType": "焼却灰",
        })
        result = await repo.get_all(waste_type="焼却灰")
        assert len(result) == 1
        assert result[0]["wasteType"] == "焼却灰"

    async def test_get_all_with_source_filter(self, async_session):
        repo = WasteRepository(async_session)
        await repo.create({
            "source": "工場X", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        await repo.create({
            "source": "工場Y", "deliveryDate": "2026-01-11", "wasteType": "汚泥",
        })
        result = await repo.get_all(source="工場X")
        assert len(result) == 1

    async def test_get_all_with_limit(self, async_session):
        repo = WasteRepository(async_session)
        for i in range(5):
            await repo.create({
                "source": f"s{i}", "deliveryDate": f"2026-01-{10 + i:02d}",
                "wasteType": "汚泥",
            })
        result = await repo.get_all(limit=2)
        assert len(result) == 2

    async def test_get_by_id(self, async_session):
        repo = WasteRepository(async_session)
        created = await repo.create({
            "source": "工場Z", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
        })
        result = await repo.get_by_id(created["id"])
        assert result is not None
        assert result["source"] == "工場Z"

    async def test_get_by_id_not_found(self, async_session):
        repo = WasteRepository(async_session)
        result = await repo.get_by_id("nonexistent-id")
        # SQLite may raise an error for non-UUID strings, which returns None
        assert result is None


@pytest.mark.unit
class TestWasteRepositoryUpdate:
    async def test_update_record(self, async_session):
        repo = WasteRepository(async_session)
        created = await repo.create({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
        })
        updated = await repo.update(created["id"], {"status": "analyzed", "notes": "更新済み"})
        assert updated is not None
        assert updated["status"] == "analyzed"
        assert updated["notes"] == "更新済み"

    async def test_update_analysis(self, async_session):
        repo = WasteRepository(async_session)
        created = await repo.create({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
        })
        updated = await repo.update(created["id"], {
            "analysis": {"pH": 8.5, "Pb": 0.003},
        })
        assert updated is not None
        assert updated["analysis"]["pH"] == 8.5

    async def test_update_all_fields(self, async_session):
        """Cover all field mappings in update method."""
        repo = WasteRepository(async_session)
        created = await repo.create({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
            "weight": 5.0, "weightUnit": "t",
        })
        updated = await repo.update(created["id"], {
            "source": "工場B",
            "deliveryDate": "2026-02-01",
            "wasteType": "焼却灰",
            "weight": 12.0,
            "weightUnit": "kg",
            "status": "formulated",
            "analysis": {"pH": 7.5},
            "formulation": {"type": "セメント", "amount": 100},
            "elutionResult": {"Pb": 0.005, "passed": True},
            "notes": "全フィールド更新テスト",
        })
        assert updated is not None
        assert updated["source"] == "工場B"
        assert updated["wasteType"] == "焼却灰"
        assert updated["weight"] == 12.0
        assert updated["weightUnit"] == "kg"
        assert updated["status"] == "formulated"
        assert updated["formulation"]["type"] == "セメント"
        assert updated["elutionResult"]["passed"] is True
        assert updated["notes"] == "全フィールド更新テスト"


@pytest.mark.unit
class TestWasteRepositoryDelete:
    async def test_delete_record(self, async_session):
        repo = WasteRepository(async_session)
        created = await repo.create({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
        })
        success = await repo.delete(created["id"])
        assert success is True

        # Confirm deleted
        result = await repo.get_by_id(created["id"])
        assert result is None

    async def test_delete_nonexistent(self, async_session):
        repo = WasteRepository(async_session)
        import uuid
        success = await repo.delete(str(uuid.uuid4()))
        assert success is False


# ===========================================================================
# MaterialTypeRepository
# ===========================================================================


@pytest.mark.unit
class TestMaterialTypeRepositoryCreate:
    async def test_create_material_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        data = {
            "name": "普通ポルトランドセメント",
            "category": "solidifier",
            "description": "一般的な固化材",
            "supplier": "太平洋セメント",
            "unitCost": 15000,
            "unit": "t",
        }
        result = await repo.create(data)
        assert result is not None
        assert result["name"] == "普通ポルトランドセメント"
        assert result["category"] == "solidifier"


@pytest.mark.unit
class TestMaterialTypeRepositoryRead:
    async def test_get_all_empty(self, async_session):
        repo = MaterialTypeRepository(async_session)
        result = await repo.get_all()
        assert result == []

    async def test_get_all_with_filter(self, async_session):
        repo = MaterialTypeRepository(async_session)
        await repo.create({"name": "セメントA", "category": "solidifier"})
        await repo.create({"name": "キレート剤A", "category": "suppressant"})
        result = await repo.get_all(category="solidifier")
        assert len(result) == 1
        assert result[0]["name"] == "セメントA"

    async def test_get_by_id(self, async_session):
        repo = MaterialTypeRepository(async_session)
        created = await repo.create({"name": "セメントB", "category": "solidifier"})
        result = await repo.get_by_id(created["id"])
        assert result is not None
        assert result["name"] == "セメントB"

    async def test_get_by_id_not_found(self, async_session):
        repo = MaterialTypeRepository(async_session)
        result = await repo.get_by_id("nonexistent-id")
        assert result is None


@pytest.mark.unit
class TestMaterialTypeRepositoryUpdate:
    async def test_update_material_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        created = await repo.create({"name": "セメントC", "category": "solidifier"})
        updated = await repo.update(created["id"], {
            "name": "高炉セメントB種",
            "description": "変更後の説明",
        })
        assert updated is not None
        assert updated["name"] == "高炉セメントB種"
        assert updated["description"] == "変更後の説明"

    async def test_update_all_fields(self, async_session):
        """Cover all field mappings in MaterialType update."""
        repo = MaterialTypeRepository(async_session)
        created = await repo.create({
            "name": "セメントC2", "category": "solidifier",
        })
        updated = await repo.update(created["id"], {
            "name": "更新セメント",
            "category": "suppressant",
            "description": "全フィールド更新",
            "supplier": "新サプライヤー",
            "unitCost": 20000,
            "unit": "kg",
            "attributes": [{"key": "val"}],
        })
        assert updated is not None
        assert updated["name"] == "更新セメント"
        assert updated["category"] == "suppressant"
        assert updated["supplier"] == "新サプライヤー"
        assert updated["unitCost"] == 20000
        assert updated["unit"] == "kg"


@pytest.mark.unit
class TestMaterialTypeRepositoryDelete:
    async def test_delete_material_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        created = await repo.create({"name": "セメントD", "category": "solidifier"})
        success = await repo.delete(created["id"])
        assert success is True

    async def test_delete_nonexistent(self, async_session):
        repo = MaterialTypeRepository(async_session)
        import uuid
        success = await repo.delete(str(uuid.uuid4()))
        assert success is False


# ===========================================================================
# WasteService
# ===========================================================================


@pytest.mark.unit
class TestWasteService:
    async def test_create_record(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        result = await svc.create_record({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
        })
        assert result is not None

    async def test_create_record_auto_status(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        result = await svc.create_record({
            "source": "工場A", "deliveryDate": "2026-01-15", "wasteType": "汚泥",
            "status": "pending",
            "analysis": {"pH": 7.0, "Pb": 0.005},
        })
        assert result is not None
        assert result["status"] == "analyzed"

    async def test_get_all_records(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        await svc.create_record({
            "source": "A", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        result = await svc.get_all_records()
        assert len(result) == 1

    async def test_get_record(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        created = await svc.create_record({
            "source": "A", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        result = await svc.get_record(created["id"])
        assert result is not None

    async def test_update_record(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        created = await svc.create_record({
            "source": "A", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        result = await svc.update_record(created["id"], {"notes": "更新"})
        assert result is not None
        assert result["notes"] == "更新"

    async def test_delete_record(self, async_session):
        repo = WasteRepository(async_session)
        svc = WasteService(repo)
        created = await svc.create_record({
            "source": "A", "deliveryDate": "2026-01-10", "wasteType": "汚泥",
        })
        success = await svc.delete_record(created["id"])
        assert success is True


# ===========================================================================
# MaterialTypeService
# ===========================================================================


@pytest.mark.unit
class TestMaterialTypeService:
    async def test_create_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        svc = MaterialTypeService(repo)
        result = await svc.create_type({"name": "セメントE", "category": "solidifier"})
        assert result is not None

    async def test_get_all_types(self, async_session):
        repo = MaterialTypeRepository(async_session)
        svc = MaterialTypeService(repo)
        await svc.create_type({"name": "セメントF", "category": "solidifier"})
        result = await svc.get_all_types()
        assert len(result) == 1

    async def test_get_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        svc = MaterialTypeService(repo)
        created = await svc.create_type({"name": "セメントG", "category": "solidifier"})
        result = await svc.get_type(created["id"])
        assert result is not None

    async def test_update_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        svc = MaterialTypeService(repo)
        created = await svc.create_type({"name": "セメントH", "category": "solidifier"})
        result = await svc.update_type(created["id"], {"description": "更新"})
        assert result is not None

    async def test_delete_type(self, async_session):
        repo = MaterialTypeRepository(async_session)
        svc = MaterialTypeService(repo)
        created = await svc.create_type({"name": "セメントI", "category": "solidifier"})
        success = await svc.delete_type(created["id"])
        assert success is True
