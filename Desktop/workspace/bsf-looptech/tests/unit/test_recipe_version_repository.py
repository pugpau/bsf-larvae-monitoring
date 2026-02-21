"""Unit tests for recipe version management in RecipeRepository."""

import uuid

import pytest

from src.materials.repository import RecipeRepository, SupplierRepository


# ══════════════════════════════════════
#  Helpers — seed data
# ══════════════════════════════════════

async def _seed_supplier(session) -> dict:
    repo = SupplierRepository(session)
    return await repo.create({
        "name": "テスト搬入先",
        "waste_types": ["汚泥"],
        "is_active": True,
    })


async def _seed_recipe(session, **overrides) -> dict:
    repo = RecipeRepository(session)
    data = {
        "name": "テストレシピ",
        "waste_type": "汚泥",
        "status": "draft",
        "notes": "テスト用",
        "details": [
            {
                "material_id": str(uuid.uuid4()),
                "material_type": "solidification",
                "addition_rate": 150.0,
                "order_index": 0,
            },
        ],
        **overrides,
    }
    return await repo.create(data)


# ══════════════════════════════════════
#  Version Snapshot on Update
# ══════════════════════════════════════

class TestUpdateCreatesVersionSnapshot:
    @pytest.mark.asyncio
    async def test_update_creates_version_snapshot(self, async_session):
        """Updating a recipe should create a version 1 snapshot."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        updated = await repo.update(str(recipe["id"]), {"name": "更新レシピ"})
        assert updated["name"] == "更新レシピ"
        assert updated["current_version"] == 2

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["name"] == "テストレシピ"

    @pytest.mark.asyncio
    async def test_version_auto_increment(self, async_session):
        """Each actual change should increment the version number."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2"})
        await repo.update(str(recipe["id"]), {"name": "v3"})
        await repo.update(str(recipe["id"]), {"name": "v4"})

        updated = await repo.get_by_id(str(recipe["id"]))
        assert updated["current_version"] == 4

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 3
        version_numbers = [v["version"] for v in versions]
        assert sorted(version_numbers) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_no_op_update_skips_snapshot(self, async_session):
        """Updating with the same value should NOT create a version snapshot."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "テストレシピ"})

        updated = await repo.get_by_id(str(recipe["id"]))
        assert updated["current_version"] == 1

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 0

    @pytest.mark.asyncio
    async def test_snapshot_preserves_details(self, async_session):
        """Version snapshot should include recipe details."""
        mat_id = str(uuid.uuid4())
        recipe = await _seed_recipe(async_session, details=[
            {
                "material_id": mat_id,
                "material_type": "solidification",
                "addition_rate": 100.0,
                "order_index": 0,
                "notes": "セメント",
            },
        ])
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "更新"})

        version = await repo.get_version(str(recipe["id"]), 1)
        assert version is not None
        assert len(version["details"]) == 1
        assert version["details"][0]["material_id"] == uuid.UUID(mat_id)
        assert version["details"][0]["addition_rate"] == 100.0
        assert version["details"][0]["notes"] == "セメント"

    @pytest.mark.asyncio
    async def test_change_summary_stored(self, async_session):
        """change_summary from update data should be stored in version."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {
            "name": "変更後",
            "change_summary": "名前を変更",
        })

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 1
        assert versions[0]["change_summary"] == "名前を変更"


# ══════════════════════════════════════
#  Get Versions
# ══════════════════════════════════════

class TestGetVersions:
    @pytest.mark.asyncio
    async def test_get_versions_returns_ordered_list(self, async_session):
        """Versions should be returned in descending order."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2"})
        await repo.update(str(recipe["id"]), {"name": "v3"})

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 2
        assert versions[0]["version"] > versions[1]["version"]
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    @pytest.mark.asyncio
    async def test_get_versions_empty_for_new_recipe(self, async_session):
        """A new recipe should have no version history."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        versions = await repo.get_versions(str(recipe["id"]))
        assert versions == []


# ══════════════════════════════════════
#  Get Specific Version
# ══════════════════════════════════════

class TestGetVersion:
    @pytest.mark.asyncio
    async def test_get_version_with_details(self, async_session):
        """Should return a specific version with its details."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2"})

        version = await repo.get_version(str(recipe["id"]), 1)
        assert version is not None
        assert version["version"] == 1
        assert version["name"] == "テストレシピ"
        assert "details" in version

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, async_session):
        """Should return None for non-existent version."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        version = await repo.get_version(str(recipe["id"]), 999)
        assert version is None


# ══════════════════════════════════════
#  Rollback
# ══════════════════════════════════════

class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_restores_header(self, async_session):
        """Rollback should restore recipe header fields from target version."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        # v1 → v2 (name change)
        await repo.update(str(recipe["id"]), {"name": "v2名"})
        # v2 → v3 (another change)
        await repo.update(str(recipe["id"]), {"name": "v3名"})

        # Rollback to v1
        result = await repo.rollback_to_version(str(recipe["id"]), 1)
        assert result is not None
        assert result["name"] == "テストレシピ"
        assert result["current_version"] == 4  # v3 snapshotted, then v4

    @pytest.mark.asyncio
    async def test_rollback_restores_details(self, async_session):
        """Rollback should restore recipe details from the target version."""
        mat_id_1 = str(uuid.uuid4())
        mat_id_2 = str(uuid.uuid4())
        recipe = await _seed_recipe(async_session, details=[
            {
                "material_id": mat_id_1,
                "material_type": "solidification",
                "addition_rate": 100.0,
                "order_index": 0,
            },
        ])
        repo = RecipeRepository(async_session)

        # Update name to create v1 snapshot
        await repo.update(str(recipe["id"]), {"name": "v2名"})

        # Add a second detail (changes current state)
        await repo.add_detail(str(recipe["id"]), {
            "material_id": mat_id_2,
            "material_type": "suppressant",
            "addition_rate": 5.0,
            "order_index": 1,
        })

        # Rollback to v1 (which had only mat_id_1)
        result = await repo.rollback_to_version(str(recipe["id"]), 1)
        assert len(result["details"]) == 1
        assert str(result["details"][0]["material_id"]) == mat_id_1

    @pytest.mark.asyncio
    async def test_rollback_snapshots_current_state(self, async_session):
        """Rollback should create a snapshot of the current state before restoring."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2名"})

        # Now rollback to v1
        await repo.rollback_to_version(str(recipe["id"]), 1)

        # Should have 2 snapshots: v1 (from update) and v2 (from rollback)
        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 2
        version_numbers = sorted([v["version"] for v in versions])
        assert version_numbers == [1, 2]

        # v2 snapshot should have change_summary about rollback
        v2 = await repo.get_version(str(recipe["id"]), 2)
        assert "Rolled back" in v2["change_summary"]

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_version(self, async_session):
        """Rollback to non-existent version should return None."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        result = await repo.rollback_to_version(str(recipe["id"]), 999)
        assert result is None


# ══════════════════════════════════════
#  Diff
# ══════════════════════════════════════

# ══════════════════════════════════════
#  Detail Changes Create Version Snapshots
# ══════════════════════════════════════

class TestDetailChangeCreatesVersion:
    @pytest.mark.asyncio
    async def test_add_detail_creates_version_snapshot(self, async_session):
        """Adding a detail should snapshot current state and increment version."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        mat_id_new = str(uuid.uuid4())
        result = await repo.add_detail(str(recipe["id"]), {
            "material_id": mat_id_new,
            "material_type": "suppressant",
            "addition_rate": 5.0,
            "order_index": 1,
        })

        assert result["current_version"] == 2
        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["change_summary"] == "明細追加: suppressant"

    @pytest.mark.asyncio
    async def test_remove_detail_creates_version_snapshot(self, async_session):
        """Removing a detail should snapshot current state and increment version."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)
        detail_id = str(recipe["details"][0]["id"])

        removed = await repo.remove_detail(str(recipe["id"]), detail_id)
        assert removed is True

        updated = await repo.get_by_id(str(recipe["id"]))
        assert updated["current_version"] == 2

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 1
        assert versions[0]["change_summary"] == "明細削除"

    @pytest.mark.asyncio
    async def test_add_detail_snapshot_preserves_details(self, async_session):
        """Version snapshot from add_detail should contain the BEFORE-state details."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        mat_id_new = str(uuid.uuid4())
        await repo.add_detail(str(recipe["id"]), {
            "material_id": mat_id_new,
            "material_type": "suppressant",
            "addition_rate": 3.0,
            "order_index": 1,
        })

        version = await repo.get_version(str(recipe["id"]), 1)
        assert version is not None
        # v1 snapshot should have original 1 detail, not 2
        assert len(version["details"]) == 1

    @pytest.mark.asyncio
    async def test_remove_detail_nonexistent_recipe(self, async_session):
        """remove_detail on nonexistent recipe should return False."""
        repo = RecipeRepository(async_session)
        result = await repo.remove_detail(
            str(uuid.uuid4()), str(uuid.uuid4()),
        )
        assert result is False


# ══════════════════════════════════════
#  created_by Tracking
# ══════════════════════════════════════

class TestCreatedByTracking:
    @pytest.mark.asyncio
    async def test_update_with_created_by(self, async_session):
        """created_by should be stored in the version snapshot."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)
        user_id = uuid.uuid4()

        await repo.update(
            str(recipe["id"]),
            {"name": "更新"},
            created_by=user_id,
        )

        versions = await repo.get_versions(str(recipe["id"]))
        assert len(versions) == 1
        assert versions[0]["created_by"] == user_id

    @pytest.mark.asyncio
    async def test_add_detail_with_created_by(self, async_session):
        """created_by should be stored when adding a detail."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)
        user_id = uuid.uuid4()

        await repo.add_detail(
            str(recipe["id"]),
            {
                "material_id": str(uuid.uuid4()),
                "material_type": "solidification",
                "addition_rate": 10.0,
                "order_index": 1,
            },
            created_by=user_id,
        )

        versions = await repo.get_versions(str(recipe["id"]))
        assert versions[0]["created_by"] == user_id


# ══════════════════════════════════════
#  Diff with Current
# ══════════════════════════════════════

class TestDiffWithCurrent:
    @pytest.mark.asyncio
    async def test_diff_with_current_detects_header(self, async_session):
        """diff_with_current should detect header changes vs live recipe."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2名"})
        await repo.update(str(recipe["id"]), {"name": "v3名"})

        diff = await repo.diff_with_current(str(recipe["id"]), 1)
        assert diff is not None
        assert diff["version_from"] == 1
        assert diff["version_to"] == 3
        changed_fields = {c["field"] for c in diff["header_changes"]}
        assert "name" in changed_fields

    @pytest.mark.asyncio
    async def test_diff_with_current_nonexistent_version(self, async_session):
        """diff_with_current with non-existent version returns None."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        diff = await repo.diff_with_current(str(recipe["id"]), 999)
        assert diff is None


class TestDiffVersions:
    @pytest.mark.asyncio
    async def test_diff_header_changes(self, async_session):
        """Diff should detect header field changes between versions."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2名", "status": "active"})
        await repo.update(str(recipe["id"]), {"name": "v3名"})

        diff = await repo.diff_versions(str(recipe["id"]), 1, 2)
        assert diff is not None
        changed_fields = {c["field"] for c in diff["header_changes"]}
        assert "name" in changed_fields
        assert "status" in changed_fields

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, async_session):
        """Diff between identical versions should show no changes."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        await repo.update(str(recipe["id"]), {"name": "v2名"})

        diff = await repo.diff_versions(str(recipe["id"]), 1, 1)
        assert diff is not None
        assert diff["header_changes"] == []
        assert diff["details_added"] == []
        assert diff["details_removed"] == []
        assert diff["details_modified"] == []

    @pytest.mark.asyncio
    async def test_diff_nonexistent_version(self, async_session):
        """Diff with a non-existent version should return None."""
        recipe = await _seed_recipe(async_session)
        repo = RecipeRepository(async_session)

        diff = await repo.diff_versions(str(recipe["id"]), 1, 999)
        assert diff is None
